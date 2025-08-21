"""
Test Dameng SQL executor
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tortoise.backends.dameng.executor import DmExecutor


class TestDmExecutor(unittest.TestCase):
    """Test Dameng SQL executor"""

    def setUp(self):
        """Set up test fixtures"""
        self.connection = MagicMock()
        self.executor = DmExecutor(self.connection, None)

    def test_parameter_conversion(self):
        """Test parameter placeholder conversion from :1 to ?"""
        # Simple case
        sql = "SELECT * FROM users WHERE id = :1"
        converted = self.executor._convert_parameters(sql)
        self.assertEqual(converted, "SELECT * FROM users WHERE id = ?")
        
        # Multiple parameters
        sql = "SELECT * FROM users WHERE id = :1 AND name = :2"
        converted = self.executor._convert_parameters(sql)
        self.assertEqual(converted, "SELECT * FROM users WHERE id = ? AND name = ?")
        
        # Out of order parameters
        sql = "SELECT * FROM users WHERE name = :2 AND id = :1"
        converted = self.executor._convert_parameters(sql)
        self.assertEqual(converted, "SELECT * FROM users WHERE name = ? AND id = ?")
        
        # Parameters in complex query
        sql = """
        INSERT INTO users (id, name, email) 
        VALUES (:1, :2, :3)
        """
        converted = self.executor._convert_parameters(sql)
        expected = """
        INSERT INTO users (id, name, email) 
        VALUES (?, ?, ?)
        """
        self.assertEqual(converted, expected)

    def test_parameter_reordering(self):
        """Test parameter value reordering"""
        # In order parameters
        sql = "SELECT * FROM users WHERE id = :1 AND name = :2"
        values = [1, "John"]
        new_sql, new_values = self.executor._reorder_parameters(sql, values)
        self.assertEqual(new_sql, "SELECT * FROM users WHERE id = ? AND name = ?")
        self.assertEqual(new_values, [1, "John"])
        
        # Out of order parameters
        sql = "SELECT * FROM users WHERE name = :2 AND id = :1"
        values = [1, "John"]
        new_sql, new_values = self.executor._reorder_parameters(sql, values)
        self.assertEqual(new_sql, "SELECT * FROM users WHERE name = ? AND id = ?")
        self.assertEqual(new_values, ["John", 1])
        
        # Repeated parameters
        sql = "SELECT * FROM users WHERE id = :1 OR parent_id = :1"
        values = [1]
        new_sql, new_values = self.executor._reorder_parameters(sql, values)
        self.assertEqual(new_sql, "SELECT * FROM users WHERE id = ? OR parent_id = ?")
        self.assertEqual(new_values, [1, 1])

    def test_no_parameters(self):
        """Test queries without parameters"""
        sql = "SELECT * FROM users"
        converted = self.executor._convert_parameters(sql)
        self.assertEqual(converted, sql)
        
        new_sql, new_values = self.executor._reorder_parameters(sql, [])
        self.assertEqual(new_sql, sql)
        self.assertEqual(new_values, [])

    async def test_execute_insert(self):
        """Test execute_insert method"""
        cursor = MagicMock()
        cursor.execute = MagicMock()
        cursor.lastrowid = 123
        
        with patch.object(self.executor, 'acquire_cursor') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = cursor
            
            sql = "INSERT INTO users (name) VALUES (:1)"
            result = await self.executor.execute_insert(sql, ["John"])
            
            cursor.execute.assert_called_once_with(
                "INSERT INTO users (name) VALUES (?)",
                ["John"]
            )
            self.assertEqual(result, 123)

    async def test_execute_many(self):
        """Test execute_many method"""
        cursor = MagicMock()
        cursor.executemany = MagicMock()
        
        with patch.object(self.executor, 'acquire_cursor') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = cursor
            
            sql = "INSERT INTO users (name, age) VALUES (:1, :2)"
            values = [["John", 25], ["Jane", 30]]
            
            await self.executor.execute_many(sql, values)
            
            cursor.executemany.assert_called_once_with(
                "INSERT INTO users (name, age) VALUES (?, ?)",
                [["John", 25], ["Jane", 30]]
            )

    async def test_execute_query(self):
        """Test execute_query method"""
        cursor = MagicMock()
        cursor.execute = MagicMock()
        cursor.fetchall = MagicMock(return_value=[
            (1, "John", 25),
            (2, "Jane", 30)
        ])
        cursor.description = [
            ("id",), ("name",), ("age",)
        ]
        
        with patch.object(self.executor, 'acquire_cursor') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = cursor
            
            sql = "SELECT * FROM users WHERE age > :1"
            result = await self.executor.execute_query(sql, [20])
            
            cursor.execute.assert_called_once_with(
                "SELECT * FROM users WHERE age > ?",
                [20]
            )
            
            # Result should be list of tuples
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], (1, "John", 25))
            self.assertEqual(result[1], (2, "Jane", 30))

    async def test_execute_query_dict(self):
        """Test execute_query_dict method"""
        cursor = MagicMock()
        cursor.execute = MagicMock()
        cursor.fetchall = MagicMock(return_value=[
            (1, "John", 25),
            (2, "Jane", 30)
        ])
        cursor.description = [
            ("id",), ("name",), ("age",)
        ]
        
        with patch.object(self.executor, 'acquire_cursor') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = cursor
            
            sql = "SELECT * FROM users WHERE age > :1"
            result = await self.executor.execute_query_dict(sql, [20])
            
            cursor.execute.assert_called_once_with(
                "SELECT * FROM users WHERE age > ?",
                [20]
            )
            
            # Result should be list of dicts
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], {"id": 1, "name": "John", "age": 25})
            self.assertEqual(result[1], {"id": 2, "name": "Jane", "age": 30})

    def test_complex_parameter_patterns(self):
        """Test complex parameter patterns"""
        # Parameters in subqueries
        sql = """
        SELECT * FROM users 
        WHERE id IN (SELECT user_id FROM orders WHERE total > :1)
        AND created_at > :2
        """
        converted = self.executor._convert_parameters(sql)
        expected = """
        SELECT * FROM users 
        WHERE id IN (SELECT user_id FROM orders WHERE total > ?)
        AND created_at > ?
        """
        self.assertEqual(converted, expected)
        
        # Parameters with similar numbers
        sql = "SELECT * FROM table WHERE col1 = :1 AND col12 = :12 AND col2 = :2"
        values = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
        new_sql, new_values = self.executor._reorder_parameters(sql, values)
        self.assertEqual(
            new_sql,
            "SELECT * FROM table WHERE col1 = ? AND col12 = ? AND col2 = ?"
        )
        self.assertEqual(new_values, ["a", "l", "b"])

    def test_edge_cases(self):
        """Test edge cases in parameter conversion"""
        # Empty SQL
        sql = ""
        converted = self.executor._convert_parameters(sql)
        self.assertEqual(converted, "")
        
        # SQL with no spaces around parameters
        sql = "WHERE id=:1AND name=:2"
        converted = self.executor._convert_parameters(sql)
        self.assertEqual(converted, "WHERE id=?AND name=?")
        
        # Parameters at the end
        sql = "WHERE id = :1"
        converted = self.executor._convert_parameters(sql)
        self.assertEqual(converted, "WHERE id = ?")

    def test_parameter_boundary(self):
        """Test parameter boundary detection"""
        # Ensure :1 in col:1 is replaced but not in col:1name
        sql = "SELECT col:1, col:1name, :1 FROM table"
        converted = self.executor._convert_parameters(sql)
        # Only the standalone :1 should be replaced
        self.assertEqual(converted, "SELECT col:1, col:1name, ? FROM table")