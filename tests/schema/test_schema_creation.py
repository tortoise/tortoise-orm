"""Tests for automatic PostgreSQL schema creation functionality."""

from tortoise.backends.base_postgres.schema_generator import BasePostgresSchemaGenerator
from tortoise.contrib import test


class TestPostgresSchemaCreation(test.TestCase):
    """Test automatic PostgreSQL schema creation."""

    def test_postgres_schema_creation_sql(self):
        """Test that BasePostgresSchemaGenerator can create schema SQL."""
        # Mock client for testing
        class MockClient:
            def __init__(self):
                self.capabilities = type('obj', (object,), {
                    'inline_comment': False,
                    'safe': True
                })()

        mock_client = MockClient()
        generator = BasePostgresSchemaGenerator(mock_client)
        
        # Test schema creation SQL generation
        schema_sql = generator._get_create_schema_sql("pgdev", safe=True)
        self.assertEqual(schema_sql, 'CREATE SCHEMA IF NOT EXISTS "pgdev";')
        
        schema_sql_unsafe = generator._get_create_schema_sql("pgdev", safe=False)
        self.assertEqual(schema_sql_unsafe, 'CREATE SCHEMA "pgdev";')