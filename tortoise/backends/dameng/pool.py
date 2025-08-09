"""Dameng database connection pool implementation.

Supports connection management, health checks, and fault recovery.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import dmPython

from tortoise.log import db_client_logger

logger = db_client_logger


@dataclass
class ConnectionInfo:
    """Connection information - Tracks connection state and usage"""
    
    connection: Any
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    in_use: bool = False
    is_healthy: bool = True
    use_count: int = 0
    
    def mark_used(self) -> None:
        """Mark connection as used"""
        self.last_used_at = time.time()
        self.use_count += 1
    
    def is_idle_too_long(self, max_idle_time: int) -> bool:
        """Check if connection has been idle too long"""
        return time.time() - self.last_used_at > max_idle_time
    
    def is_expired(self, max_lifetime: int = 3600) -> bool:
        """Check if connection is expired (default 1 hour)"""
        return time.time() - self.created_at > max_lifetime


class DmConnectionPool:
    """Dameng database connection pool - Enterprise-grade connection management"""
    
    def __init__(
        self,
        connection_config: Dict[str, Any],
        min_size: int = 1,
        max_size: int = 10,
        max_idle_time: int = 300,  # 5 minutes
        acquire_timeout: int = 30,  # 30 seconds
        health_check_interval: int = 60,  # 1 minute
        max_lifetime: int = 3600,  # 1 hour
        executor: Optional[ThreadPoolExecutor] = None
    ) -> None:
        """Initialize connection pool.
        
        Args:
            connection_config: Database connection configuration
            min_size: Minimum number of connections
            max_size: Maximum number of connections
            max_idle_time: Maximum idle time in seconds
            acquire_timeout: Timeout for acquiring connection in seconds
            health_check_interval: Health check interval in seconds
            max_lifetime: Maximum connection lifetime in seconds
            executor: Thread pool executor
        """
        self._config = connection_config.copy()
        self._min_size = max(1, min_size)
        self._max_size = max(min_size, max_size)
        self._max_idle_time = max_idle_time
        self._acquire_timeout = acquire_timeout
        self._health_check_interval = health_check_interval
        self._max_lifetime = max_lifetime
        
        # Connection pool state
        self._connections: List[ConnectionInfo] = []
        self._lock = asyncio.Lock()
        self._closed = False
        self._initialized = False
        
        # Statistics
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'created_connections': 0,
            'closed_connections': 0,
            'failed_connections': 0,
            'acquire_timeouts': 0,
            'health_check_failures': 0,
        }
        
        # Thread pool for executing synchronous database operations
        self._executor = executor or ThreadPoolExecutor(max_workers=max_size * 2)
        self._own_executor = executor is None
        
        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"Connection pool initialized - min: {self._min_size}, max: {self._max_size}, "
            f"database: {self._config['database']}"
        )
    
    async def initialize(self) -> None:
        """Initialize connection pool - Create minimum connections"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            try:
                # Create minimum connections
                for i in range(self._min_size):
                    try:
                        conn_info = await self._create_connection()
                        self._connections.append(conn_info)
                        self._stats['created_connections'] += 1
                        logger.debug(f"Created initial connection {i+1}/{self._min_size}")
                    except Exception as e:
                        logger.error(f"Failed to create initial connection: {e}")
                        if i == 0:  # If first connection fails, raise exception
                            raise
                
                # Start health check task
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                
                self._initialized = True
                self._stats['total_connections'] = len(self._connections)
                
                logger.info(f"Connection pool initialized - current connections: {len(self._connections)}")
                
            except Exception as e:
                logger.error(f"Connection pool initialization failed: {e}")
                await self.close()
                raise
    
    async def _create_connection(self) -> ConnectionInfo:
        """Create new database connection"""
        try:
            # Create synchronous connection in thread pool
            connection = await asyncio.get_event_loop().run_in_executor(
                self._executor, self._create_sync_connection
            )
            
            conn_info = ConnectionInfo(connection=connection)
            logger.debug(f"Successfully created connection to {self._config['host']}:{self._config['port']}")
            
            return conn_info
            
        except Exception as e:
            self._stats['failed_connections'] += 1
            logger.error(f"Failed to create connection: {e}")
            raise
    
    def _create_sync_connection(self) -> dmPython.Connection:
        """Create synchronous database connection (executed in thread pool)"""
        try:
            connection = dmPython.connect(
                self._config['user'],
                self._config['password'],
                f"{self._config['host']}:{self._config['port']}",
                self._config['database']
            )
            
            # dmPython connections are in autocommit mode by default
            # Transactions are managed explicitly via commit/rollback
            
            # Set charset if supported
            if hasattr(connection, 'set_charset') and self._config.get('charset'):
                try:
                    connection.set_charset(self._config['charset'])
                except Exception:
                    pass  # Ignore charset setting failures
            
            return connection
            
        except Exception as e:
            raise Exception(f"Failed to create dmPython connection: {e}")
    
    async def acquire(self) -> dmPython.Connection:
        """Acquire connection - Supports timeout and connection reuse"""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        while True:
            async with self._lock:
                # Find available connection
                for conn_info in self._connections:
                    if not conn_info.in_use and conn_info.is_healthy:
                        # Check if connection is expired
                        if conn_info.is_expired(self._max_lifetime):
                            await self._close_connection(conn_info)
                            continue
                        
                        # Check connection health
                        if await self._is_connection_healthy(conn_info):
                            conn_info.in_use = True
                            conn_info.mark_used()
                            self._stats['active_connections'] = sum(
                                1 for c in self._connections if c.in_use
                            )
                            logger.debug(
                                f"Reused connection - active: {self._stats['active_connections']}"
                            )
                            return conn_info.connection
                        else:
                            await self._close_connection(conn_info)
                
                # If no available connection and not at max, create new one
                if len(self._connections) < self._max_size:
                    try:
                        conn_info = await self._create_connection()
                        conn_info.in_use = True
                        conn_info.mark_used()
                        self._connections.append(conn_info)
                        
                        self._stats['created_connections'] += 1
                        self._stats['total_connections'] = len(self._connections)
                        self._stats['active_connections'] = sum(
                            1 for c in self._connections if c.in_use
                        )
                        
                        logger.debug(
                            f"Created new connection - total: {len(self._connections)}, "
                            f"active: {self._stats['active_connections']}"
                        )
                        return conn_info.connection
                        
                    except Exception as e:
                        logger.error(f"Failed to create new connection: {e}")
            
            # Check timeout
            if time.time() - start_time > self._acquire_timeout:
                self._stats['acquire_timeouts'] += 1
                raise asyncio.TimeoutError(f"Connection acquire timeout ({self._acquire_timeout} seconds)")
            
            # Wait before retry
            await asyncio.sleep(0.1)
    
    async def release(self, connection: dmPython.Connection) -> None:
        """Release connection back to pool"""
        if self._closed:
            return
        
        async with self._lock:
            for conn_info in self._connections:
                if conn_info.connection == connection:
                    if conn_info.in_use:
                        conn_info.in_use = False
                        self._stats['active_connections'] = sum(
                            1 for c in self._connections if c.in_use
                        )
                        logger.debug(f"Released connection - active: {self._stats['active_connections']}")
                    return
        
        # If connection not found, it might be a cleaned up connection, close it
        logger.warning("Releasing unknown connection, closing directly")
        try:
            await asyncio.get_event_loop().run_in_executor(None, connection.close)
        except Exception:
            pass
    
    async def _is_connection_healthy(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is healthy"""
        try:
            # Execute simple query to test connection
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, conn_info.connection.cursor
            )
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, "SELECT 1"
            )
            
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.close
            )
            
            conn_info.is_healthy = True
            return True
            
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            conn_info.is_healthy = False
            return False
    
    async def _close_connection(self, conn_info: ConnectionInfo) -> None:
        """Close single connection"""
        try:
            if conn_info in self._connections:
                self._connections.remove(conn_info)
            
            await asyncio.get_event_loop().run_in_executor(
                None, conn_info.connection.close
            )
            
            self._stats['closed_connections'] += 1
            self._stats['total_connections'] = len(self._connections)
            
            logger.debug(f"Closed connection - remaining connections: {len(self._connections)}")
            
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    async def _health_check_loop(self) -> None:
        """Health check loop - Periodically clean up invalid connections"""
        while not self._closed:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self._closed:
                    break
                
                await self._perform_health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def _perform_health_check(self) -> None:
        """Perform health check - Clean up invalid and idle connections"""
        async with self._lock:
            connections_to_remove = []
            
            for conn_info in self._connections:
                if conn_info.in_use:
                    continue
                
                # Check if connection is expired or idle too long
                if conn_info.is_expired(self._max_lifetime) or \
                   conn_info.is_idle_too_long(self._max_idle_time):
                    connections_to_remove.append(conn_info)
                    continue
                
                # Health check
                if not await self._is_connection_healthy(conn_info):
                    connections_to_remove.append(conn_info)
                    self._stats['health_check_failures'] += 1
            
            # Remove invalid connections
            for conn_info in connections_to_remove:
                await self._close_connection(conn_info)
            
            # Ensure minimum connections
            current_count = len(self._connections)
            if current_count < self._min_size:
                needed = self._min_size - current_count
                logger.info(f"Connection count below minimum, need to create {needed} connections")
                
                for i in range(needed):
                    try:
                        conn_info = await self._create_connection()
                        self._connections.append(conn_info)
                        self._stats['created_connections'] += 1
                        logger.debug(f"Created connection in health check {i+1}/{needed}")
                    except Exception as e:
                        logger.error(f"Failed to create connection in health check: {e}")
                        break
                
                self._stats['total_connections'] = len(self._connections)
            
            if connections_to_remove:
                logger.info(
                    f"Health check completed - removed {len(connections_to_remove)} connections, "
                    f"current connections: {len(self._connections)}"
                )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        async with self._lock:
            idle_connections = sum(1 for c in self._connections if not c.in_use)
            unhealthy_connections = sum(1 for c in self._connections if not c.is_healthy)
            
            return {
                'total_connections': len(self._connections),
                'active_connections': self._stats['active_connections'],
                'idle_connections': idle_connections,
                'unhealthy_connections': unhealthy_connections,
                'min_size': self._min_size,
                'max_size': self._max_size,
                'max_idle_time': self._max_idle_time,
                'max_lifetime': self._max_lifetime,
                'statistics': self._stats.copy(),
                'initialized': self._initialized,
                'closed': self._closed,
            }
    
    async def close(self) -> None:
        """Close connection pool and all connections"""
        if self._closed:
            return
        
        logger.info("Starting connection pool shutdown")
        self._closed = True
        
        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            # Close all connections
            for conn_info in self._connections[:]:
                await self._close_connection(conn_info)
            
            self._connections.clear()
            self._stats['total_connections'] = 0
            self._stats['active_connections'] = 0
        
        # Shutdown thread pool if we created it
        if self._own_executor and self._executor:
            self._executor.shutdown(wait=True)
        
        logger.info("Connection pool closed")
    
    def __del__(self) -> None:
        """Destructor - Ensure resource cleanup"""
        if not self._closed:
            logger.warning("Connection pool not properly closed, forcing cleanup")
            try:
                # Try to clean up in event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except Exception:
                pass
    
    async def __aenter__(self) -> "DmConnectionPool":
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.close()