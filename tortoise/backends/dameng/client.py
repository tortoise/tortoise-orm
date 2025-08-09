from __future__ import annotations

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import dmPython
from pypika import Query

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    Capabilities,
    ConnectionWrapper,
    NestedTransactionContext,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.exceptions import (
    DBConnectionError,
    DoesNotExist,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)
from tortoise.log import db_client_logger

from .executor import DmExecutor
from .pool import DmConnectionPool
from .schema_generator import DmSchemaGenerator

if TYPE_CHECKING:
    from tortoise.models import Model

FuncType = Callable[..., Coroutine[Any, Any, Any]]
T = TypeVar("T")

logger = db_client_logger


class DmClient(BaseDBAsyncClient):
    """Dameng database async client"""
    
    executor_class = DmExecutor
    schema_generator = DmSchemaGenerator
    query_class = Query
    
    capabilities = Capabilities(
        dialect="dm",
        daemon=False,
        requires_limit=True,
        inline_comment=True,
        supports_transactions=True,
        support_for_update=True,
        support_index_hint=False,
        support_update_limit_order_by=False,
    )
    
    def __init__(self, connection_name: str, **kwargs: Any) -> None:
        """Initialize Dameng database client with connection pooling support"""
        super().__init__(connection_name=connection_name, **kwargs)
        self._connection = None
        self._connection_params = kwargs
        self._pool: Optional[DmConnectionPool] = None
        self._thread_pool = ThreadPoolExecutor(max_workers=10)
        self._transaction_context: Dict[int, Dict[str, Any]] = {}
        
        # Connection pool configuration
        self._pool_config = {
            'min_size': kwargs.get('pool_min_size', 1),
            'max_size': kwargs.get('pool_max_size', 10),
            'max_idle_time': kwargs.get('pool_max_idle_time', 300),  # 5 minutes
            'acquire_timeout': kwargs.get('pool_acquire_timeout', 30),  # 30 seconds
        }
    
    async def create_connection(self, with_db: bool = True) -> None:
        """Create database connection with pooling support"""
        if self._pool:
            return
        
        params = self._connection_params.copy()
        
        # Build connection parameters
        connection_config = {
            'host': params.get("host", "localhost"),
            'port': params.get("port", 5236),
            'user': params.get("user", "SYSDBA"),
            'password': params.get("password", "SYSDBA"),
            'database': params.get("database", "SYSDBA"),
            'charset': params.get("charset", "utf8"),
            'connect_timeout': params.get("connect_timeout", 10),
        }
        
        try:
            # Create connection pool
            self._pool = DmConnectionPool(
                connection_config=connection_config,
                min_size=self._pool_config['min_size'],
                max_size=self._pool_config['max_size'],
                max_idle_time=self._pool_config['max_idle_time'],
                acquire_timeout=self._pool_config['acquire_timeout'],
                executor=self._thread_pool
            )
            
            # Initialize connection pool
            await self._pool.initialize()
            
            logger.info(
                f"Dameng database connection pool created - "
                f"{connection_config['host']}:{connection_config['port']}/{connection_config['database']}"
            )
            
        except Exception as e:
            error_msg = (
                f"Unable to connect to Dameng database "
                f"{connection_config['host']}:{connection_config['port']}: {e}"
            )
            logger.error(error_msg)
            raise DBConnectionError(error_msg)
    
    async def close(self) -> None:
        """Close database connection pool and all resources"""
        try:
            if self._pool:
                await self._pool.close()
                self._pool = None
            
            if self._thread_pool:
                self._thread_pool.shutdown(wait=True)
                self._thread_pool = None
            
            logger.info("Dameng database connection closed")
        except Exception as e:
            logger.error(f"Error closing Dameng database connection: {e}")
    
    async def db_create(self) -> None:
        """Create database - Usually pre-created by DBA for Dameng"""
        logger.info(f"Database {self.database} initialization check")
        
        try:
            # Check database connection
            await self.execute_query("SELECT 1")
            logger.info("Database connection is normal")
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            raise
    
    async def db_delete(self) -> None:
        """Delete database - Not supported through application for Dameng"""
        logger.warning("Dameng database does not support programmatic database deletion")
        raise NotImplementedError("Dameng database does not support programmatic database deletion")
    
    def acquire_connection(self) -> "DmClient":
        """Acquire connection - Returns current client instance for compatibility"""
        return self
    
    async def execute_query(
        self, query: str, values: Optional[List[Any]] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Execute query with connection pooling and error handling"""
        if not self._pool:
            await self.create_connection()
        
        # Convert parameters using executor method
        converted_query = self._convert_query_parameters(query) if values else query
        
        connection = None
        cursor = None
        
        try:
            # Get connection from pool
            connection = await self._pool.acquire()
            cursor = await asyncio.get_event_loop().run_in_executor(None, connection.cursor)
            
            # Execute query
            if values:
                await asyncio.get_event_loop().run_in_executor(
                    None, cursor.execute, converted_query, values
                )
            else:
                await asyncio.get_event_loop().run_in_executor(
                    None, cursor.execute, converted_query
                )
            
            # Handle results
            if query.strip().upper().startswith(("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")):
                # Query operations
                rows = await asyncio.get_event_loop().run_in_executor(None, cursor.fetchall)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                result = [dict(zip(columns, row)) for row in rows]
                return len(result), result
            else:
                # Modification operations (INSERT, UPDATE, DELETE)
                rowcount = cursor.rowcount
                # Commit if not in transaction
                if not self.in_transaction():
                    await asyncio.get_event_loop().run_in_executor(None, connection.commit)
                return rowcount, []
                
        except dmPython.Error as e:
            # dmPython specific error handling
            if connection and not self.in_transaction():
                await asyncio.get_event_loop().run_in_executor(None, connection.rollback)
            
            error_msg = str(e)
            error_code = getattr(e, 'code', 0) if hasattr(e, 'code') else 0
            
            # Categorize errors
            if "duplicate" in error_msg.lower() or error_code in [1, 2601, 2627]:
                raise IntegrityError(f"Unique constraint violation: {error_msg}")
            elif "foreign key" in error_msg.lower() or error_code in [547]:
                raise IntegrityError(f"Foreign key constraint violation: {error_msg}")
            elif "connection" in error_msg.lower() or error_code in [40001, 40197]:
                raise DBConnectionError(f"Database connection error: {error_msg}")
            elif "not found" in error_msg.lower():
                raise DoesNotExist(f"Record not found: {error_msg}")
            else:
                raise OperationalError(f"Database operation failed: {error_msg}")
                
        except Exception as e:
            # General error handling
            if connection and not self.in_transaction():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, connection.rollback)
                except Exception:
                    pass
            
            logger.error(f"Query execution failed - SQL: {query[:100]}..., Error: {e}")
            raise OperationalError(f"Query execution failed: {e}")
            
        finally:
            # Cleanup resources
            if cursor:
                try:
                    await asyncio.get_event_loop().run_in_executor(None, cursor.close)
                except Exception:
                    pass
            if connection:
                await self._pool.release(connection)
    
    async def execute_insert(self, query: str, values: List[Any]) -> int:
        """Execute insert operation - Returns affected row count"""
        try:
            rowcount, _ = await self.execute_query(query, values)
            logger.debug(f"Insert operation completed, affected {rowcount} rows")
            return rowcount
        except Exception as e:
            logger.error(f"Insert operation failed - SQL: {query[:100]}..., Error: {e}")
            raise
    
    async def execute_many(self, query: str, values: List[List[Any]]) -> None:
        """Batch execute with transaction support and error recovery"""
        if not self._pool:
            await self.create_connection()
        
        if not values:
            return
        
        # Convert parameters
        converted_query = self._convert_query_parameters(query)
        
        connection = None
        cursor = None
        
        try:
            connection = await self._pool.acquire()
            cursor = await asyncio.get_event_loop().run_in_executor(None, connection.cursor)
            
            # Execute batch operation
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.executemany, converted_query, values
            )
            
            # Commit if not in transaction
            if not self.in_transaction():
                await asyncio.get_event_loop().run_in_executor(None, connection.commit)
            
            logger.debug(f"Batch execution successful, affected {len(values)} records")
            
        except Exception as e:
            if connection and not self.in_transaction():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, connection.rollback)
                except Exception:
                    pass
            
            logger.error(
                f"Batch execution failed - SQL: {query[:100]}..., "
                f"Records: {len(values)}, Error: {e}"
            )
            raise OperationalError(f"Batch execution failed: {e}")
            
        finally:
            if cursor:
                try:
                    await asyncio.get_event_loop().run_in_executor(None, cursor.close)
                except Exception:
                    pass
            if connection:
                await self._pool.release(connection)
    
    async def execute_script(self, query: str) -> None:
        """Execute SQL script with multi-statement support and transaction handling"""
        if not query.strip():
            return
        
        # Split multiple SQL statements (considering semicolons in strings)
        statements = self._split_sql_statements(query)
        
        if not statements:
            return
        
        # Debug: print first few statements
        for i, stmt in enumerate(statements[:5]):
            logger.debug(f"Script statement {i+1}: {stmt[:200]}...")
        
        # Use transaction for multiple statements
        should_use_transaction = len(statements) > 1 and not self.in_transaction()
        
        try:
            if should_use_transaction:
                await self.start_transaction()
            
            for i, statement in enumerate(statements):
                try:
                    await self.execute_query(statement)
                    logger.debug(f"Script statement {i+1}/{len(statements)} executed successfully")
                except Exception as e:
                    logger.error(f"Script statement {i+1} failed: {statement[:50]}..., Error: {e}")
                    raise
            
            if should_use_transaction:
                await self.commit_transaction()
                
            logger.info(f"SQL script execution completed, {len(statements)} statements")
            
        except Exception as e:
            if should_use_transaction:
                await self.rollback_transaction()
            logger.error(f"SQL script execution failed: {e}")
            raise
    
    def _split_sql_statements(self, script: str) -> List[str]:
        """Intelligently split SQL statements, avoiding semicolons in strings"""
        statements = []
        current_statement = ""
        in_single_quote = False
        in_double_quote = False
        
        i = 0
        while i < len(script):
            char = script[i]
            
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == ';' and not in_single_quote and not in_double_quote:
                # Statement ends
                statement = current_statement.strip()
                if statement:
                    statements.append(statement)
                current_statement = ""
                i += 1
                continue
            
            current_statement += char
            i += 1
        
        # Add last statement
        statement = current_statement.strip()
        if statement:
            statements.append(statement)
        
        return statements
    
    async def start_transaction(self) -> None:
        """Start transaction with context management support"""
        if not self._pool:
            await self.create_connection()
        
        task_id = id(asyncio.current_task())
        
        if task_id in self._transaction_context:
            # Nested transaction, increase level
            self._transaction_context[task_id]['level'] += 1
            logger.debug(
                f"Nested transaction started, level: {self._transaction_context[task_id]['level']}"
            )
            return
        
        try:
            # Get dedicated connection for transaction
            connection = await self._pool.acquire()
            # dmPython doesn't support autocommit attribute, transactions managed via commit/rollback
            
            self._transaction_context[task_id] = {
                'connection': connection,
                'level': 1,
                'committed': False
            }
            
            logger.debug(f"Transaction started - Task ID: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            raise OperationalError(f"Failed to start transaction: {e}")
    
    async def commit_transaction(self) -> None:
        """Commit transaction with nested transaction support"""
        task_id = id(asyncio.current_task())
        
        if task_id not in self._transaction_context:
            logger.warning("Attempting to commit non-existent transaction")
            return
        
        tx_context = self._transaction_context[task_id]
        
        if tx_context['level'] > 1:
            # Nested transaction, decrease level
            tx_context['level'] -= 1
            logger.debug(f"Nested transaction level decreased to: {tx_context['level']}")
            return
        
        try:
            connection = tx_context['connection']
            await asyncio.get_event_loop().run_in_executor(None, connection.commit)
            tx_context['committed'] = True
            
            logger.debug(f"Transaction committed successfully - Task ID: {task_id}")
            
        except Exception as e:
            logger.error(f"Transaction commit failed: {e}")
            raise OperationalError(f"Transaction commit failed: {e}")
        
        finally:
            # Cleanup transaction context
            await self._cleanup_transaction(task_id)
    
    async def rollback_transaction(self) -> None:
        """Rollback transaction with nested transaction support"""
        task_id = id(asyncio.current_task())
        
        if task_id not in self._transaction_context:
            logger.warning("Attempting to rollback non-existent transaction")
            return
        
        tx_context = self._transaction_context[task_id]
        
        try:
            connection = tx_context['connection']
            await asyncio.get_event_loop().run_in_executor(None, connection.rollback)
            
            logger.debug(f"Transaction rolled back successfully - Task ID: {task_id}")
            
        except Exception as e:
            logger.error(f"Transaction rollback failed: {e}")
            raise OperationalError(f"Transaction rollback failed: {e}")
        
        finally:
            # Cleanup transaction context (rollback clears entire transaction)
            await self._cleanup_transaction(task_id)
    
    async def _cleanup_transaction(self, task_id: int) -> None:
        """Cleanup transaction context and release connection"""
        if task_id in self._transaction_context:
            tx_context = self._transaction_context[task_id]
            connection = tx_context['connection']
            
            # Release connection back to pool
            await self._pool.release(connection)
            
            # Delete transaction context
            del self._transaction_context[task_id]
    
    def in_transaction(self) -> bool:
        """Check if current task is in a transaction"""
        task_id = id(asyncio.current_task())
        return task_id in self._transaction_context
    
    def _convert_query_parameters(self, query: str) -> str:
        """Convert parameter placeholders from :1, :2 format to ? format"""
        # Save all string contents to avoid replacing parameters in strings
        strings = []
        string_pattern = re.compile(r"'[^']*'")
        
        # Temporarily replace strings with placeholders
        def save_string(match):
            strings.append(match.group(0))
            return f"__STR_{len(strings)-1}__"
        
        query_with_placeholders = string_pattern.sub(save_string, query)
        
        # Replace parameters
        query_with_placeholders = DmExecutor.PARAM_PATTERN.sub('?', query_with_placeholders)
        
        # Restore strings
        for i, string in enumerate(strings):
            query_with_placeholders = query_with_placeholders.replace(f"__STR_{i}__", string)
        
        return query_with_placeholders
    
    @property
    def database(self) -> str:
        """Get database name"""
        return self._connection_params.get("database", "SYSDBA")
    
    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection info (excluding sensitive data)"""
        return {
            "host": self._connection_params.get("host", "localhost"),
            "port": self._connection_params.get("port", 5236),
            "database": self._connection_params.get("database", "SYSDBA"),
            "user": self._connection_params.get("user", "SYSDBA"),
            "charset": self._connection_params.get("charset", "utf8"),
            "pool_config": self._pool_config
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check - Test database connection status"""
        try:
            if not self._pool:
                return {
                    "status": "unhealthy",
                    "error": "Connection pool not initialized"
                }
            
            # Execute simple query to test connection
            _, result = await self.execute_query("SELECT 1 as test")
            
            pool_status = await self._pool.get_status()
            
            return {
                "status": "healthy",
                "database": self.database,
                "pool_status": pool_status,
                "test_query": "Success" if result and result[0].get("test") == 1 else "Failed"
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def __del__(self):
        """Destructor - Ensure resource cleanup"""
        try:
            if self._pool:
                # Close asynchronously in event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
        except Exception:
            pass