"""
Test Dameng connection pool
"""

import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from tortoise.backends.dameng.pool import DmConnectionPool


class TestDmConnectionPool(unittest.TestCase):
    """Test Dameng connection pool implementation"""

    def setUp(self):
        """Set up test fixtures"""
        self.pool_config = {
            "host": "localhost",
            "port": 5236,
            "user": "SYSDBA",
            "password": "SYSDBA",
            "database": "DAMENG",
            "minsize": 1,
            "maxsize": 5,
        }

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_pool_initialization(self, mock_dm):
        """Test pool initialization"""
        pool = DmConnectionPool(**self.pool_config)
        
        self.assertEqual(pool.minsize, 1)
        self.assertEqual(pool.maxsize, 5)
        self.assertEqual(pool._size, 0)
        self.assertFalse(pool._initialized)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_pool_init(self, mock_dm):
        """Test pool init creates minimum connections"""
        mock_conn = MagicMock()
        mock_dm.connect.return_value = mock_conn
        
        pool = DmConnectionPool(**self.pool_config)
        await pool._init()
        
        # Should create minsize connections
        self.assertEqual(mock_dm.connect.call_count, 1)
        self.assertTrue(pool._initialized)
        self.assertEqual(pool._size, 1)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_acquire_connection(self, mock_dm):
        """Test acquiring a connection"""
        mock_conn = MagicMock()
        mock_dm.connect.return_value = mock_conn
        
        pool = DmConnectionPool(**self.pool_config)
        await pool._init()
        
        # Acquire connection
        async with pool.acquire() as conn:
            self.assertEqual(conn, mock_conn)
            self.assertEqual(pool._used_connections, 1)
        
        # After context exit, connection should be released
        self.assertEqual(pool._used_connections, 0)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_connection_health_check(self, mock_dm):
        """Test connection health checking"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_dm.connect.return_value = mock_conn
        
        pool = DmConnectionPool(**self.pool_config)
        
        # Test healthy connection
        mock_cursor.execute.return_value = None
        result = await pool._check_connection_health(mock_conn)
        self.assertTrue(result)
        mock_cursor.execute.assert_called_with("SELECT 1 FROM DUAL")
        
        # Test unhealthy connection
        mock_cursor.execute.side_effect = Exception("Connection lost")
        result = await pool._check_connection_health(mock_conn)
        self.assertFalse(result)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_connection_recycling(self, mock_dm):
        """Test connection recycling based on age"""
        mock_conn = MagicMock()
        mock_dm.connect.return_value = mock_conn
        
        pool = DmConnectionPool(**self.pool_config, pool_recycle=1)  # 1 second recycle
        await pool._init()
        
        # Get connection info
        conn_wrapper = pool._queue.get_nowait()
        
        # Make connection old
        conn_wrapper.created_at = datetime.now() - timedelta(seconds=2)
        
        # Put back and try to acquire - should create new connection
        pool._queue.put_nowait(conn_wrapper)
        
        async with pool.acquire() as conn:
            pass
        
        # Should have closed old connection
        mock_conn.close.assert_called()

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_pool_close(self, mock_dm):
        """Test closing the pool"""
        mock_conn1 = MagicMock()
        mock_conn2 = MagicMock()
        mock_dm.connect.side_effect = [mock_conn1, mock_conn2]
        
        pool = DmConnectionPool(**self.pool_config, minsize=2)
        await pool._init()
        
        # Close pool
        await pool.close()
        
        # All connections should be closed
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
        self.assertEqual(pool._size, 0)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_concurrent_acquire(self, mock_dm):
        """Test concurrent connection acquisition"""
        connections = []
        for i in range(5):
            mock_conn = MagicMock()
            mock_conn.id = i
            connections.append(mock_conn)
        
        mock_dm.connect.side_effect = connections
        
        pool = DmConnectionPool(**self.pool_config, minsize=1, maxsize=3)
        await pool._init()
        
        # Try to acquire more connections than maxsize
        acquired = []
        
        async def acquire_conn():
            async with pool.acquire() as conn:
                acquired.append(conn)
                await asyncio.sleep(0.1)
        
        # This should work for first 3
        tasks = [acquire_conn() for _ in range(3)]
        await asyncio.gather(*tasks)
        
        self.assertEqual(len(acquired), 3)
        self.assertEqual(pool._size, 3)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_connection_timeout(self, mock_dm):
        """Test connection acquisition timeout"""
        mock_conn = MagicMock()
        mock_dm.connect.return_value = mock_conn
        
        pool = DmConnectionPool(**self.pool_config, minsize=1, maxsize=1)
        await pool._init()
        
        # Hold one connection
        conn1 = await pool.acquire()
        
        # Try to acquire another with timeout
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(pool.acquire(), timeout=0.1)
        
        # Release first connection
        await pool.release(conn1)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_failed_connection_creation(self, mock_dm):
        """Test handling of failed connection creation"""
        mock_dm.connect.side_effect = Exception("Connection failed")
        
        pool = DmConnectionPool(**self.pool_config)
        
        with self.assertRaises(Exception):
            await pool._init()

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_connection_wrapper_properties(self, mock_dm):
        """Test ConnectionWrapper properties"""
        mock_conn = MagicMock()
        mock_dm.connect.return_value = mock_conn
        
        pool = DmConnectionPool(**self.pool_config)
        wrapper = pool.ConnectionWrapper(mock_conn)
        
        self.assertEqual(wrapper.connection, mock_conn)
        self.assertIsInstance(wrapper.created_at, datetime)
        self.assertIsInstance(wrapper.last_used, datetime)
        self.assertEqual(wrapper.use_count, 0)

    @patch("tortoise.backends.dameng.pool.dmPython")
    async def test_idle_connection_cleanup(self, mock_dm):
        """Test cleanup of idle connections"""
        mock_conn = MagicMock()
        mock_dm.connect.return_value = mock_conn
        
        # Create pool with idle timeout
        pool = DmConnectionPool(**self.pool_config, idle_timeout=1)
        await pool._init()
        
        # Get connection wrapper and make it idle
        conn_wrapper = pool._queue.get_nowait()
        conn_wrapper.last_used = datetime.now() - timedelta(seconds=2)
        pool._queue.put_nowait(conn_wrapper)
        
        # Run cleanup
        await pool._cleanup_idle_connections()
        
        # Connection should be closed and removed
        mock_conn.close.assert_called_once()
        self.assertEqual(pool._size, 0)