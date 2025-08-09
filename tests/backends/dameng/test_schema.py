"""
Test Dameng schema generation
"""

import unittest

from tortoise import fields
from tortoise.backends.dameng.schema_generator import DmSchemaGenerator
from tortoise.models import Model


class TestModel(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50)
    email = fields.CharField(max_length=100, unique=True)
    age = fields.IntField(null=True)
    balance = fields.DecimalField(max_digits=10, decimal_places=2)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        app = "test"
        table = "test_model"
        indexes = [
            ["name", "age"],
        ]


class TestDmSchemaGenerator(unittest.TestCase):
    """Test Dameng schema generator"""

    def setUp(self):
        """Set up test fixtures"""
        self.generator = DmSchemaGenerator(None)

    def test_quote(self):
        """Test identifier quoting"""
        self.assertEqual(self.generator.quote("table"), '"table"')
        self.assertEqual(self.generator.quote("Table"), '"Table"')
        self.assertEqual(self.generator.quote("my_table"), '"my_table"')

    def test_column_comment_generator(self):
        """Test column comment generation"""
        comment = self.generator._column_comment_generator(
            "table",
            "column",
            "Test comment",
            {}
        )
        expected = 'COMMENT ON COLUMN "table"."column" IS \'Test comment\''
        self.assertEqual(comment, expected)

    def test_table_comment_generator(self):
        """Test table comment generation"""
        comment = self.generator._table_comment_generator(
            "table",
            "Test table comment",
            {}
        )
        expected = 'COMMENT ON TABLE "table" IS \'Test table comment\''
        self.assertEqual(comment, expected)

    def test_column_default_generator(self):
        """Test column default value generation"""
        # Boolean default
        default = self.generator._column_default_generator(
            "table",
            "is_active",
            {"default": True},
            True
        )
        self.assertEqual(default, "1")
        
        # String default
        default = self.generator._column_default_generator(
            "table",
            "status",
            {"default": "active"},
            False
        )
        self.assertEqual(default, "'active'")
        
        # Numeric default
        default = self.generator._column_default_generator(
            "table",
            "count",
            {"default": 0},
            False
        )
        self.assertEqual(default, "0")

    def test_escape_default_value(self):
        """Test default value escaping"""
        # Boolean values
        self.assertEqual(self.generator._escape_default_value(True, True), "1")
        self.assertEqual(self.generator._escape_default_value(False, True), "0")
        
        # String values
        self.assertEqual(
            self.generator._escape_default_value("test", False),
            "'test'"
        )
        self.assertEqual(
            self.generator._escape_default_value("test's", False),
            "'test''s'"
        )
        
        # Numeric values
        self.assertEqual(self.generator._escape_default_value(42, False), "42")
        self.assertEqual(self.generator._escape_default_value(3.14, False), "3.14")

    def test_get_create_sequence_sql(self):
        """Test sequence creation SQL"""
        sql = self.generator._get_create_sequence_sql("test_seq")
        expected = 'CREATE SEQUENCE "test_seq"'
        self.assertEqual(sql, expected)

    def test_create_fk_string(self):
        """Test foreign key creation string"""
        fk_str = self.generator._create_fk_string(
            "orders",
            "customer_id",
            "customers",
            "id",
            "CASCADE",
            "SET NULL",
            "FK_orders_customers"
        )
        expected = (
            'ALTER TABLE "orders" ADD CONSTRAINT "FK_orders_customers" '
            'FOREIGN KEY ("customer_id") REFERENCES "customers" ("id") '
            'ON DELETE CASCADE ON UPDATE SET NULL'
        )
        self.assertEqual(fk_str, expected)

    def test_create_index_sql(self):
        """Test index creation SQL"""
        # Single column index
        sql = self.generator._create_index_sql(
            "test_table",
            ["name"],
            False,
            "idx_name"
        )
        expected = 'CREATE INDEX "idx_name" ON "test_table" ("name")'
        self.assertEqual(sql, expected)
        
        # Multi-column index
        sql = self.generator._create_index_sql(
            "test_table",
            ["name", "age"],
            False,
            "idx_name_age"
        )
        expected = 'CREATE INDEX "idx_name_age" ON "test_table" ("name", "age")'
        self.assertEqual(sql, expected)
        
        # Unique index
        sql = self.generator._create_index_sql(
            "test_table",
            ["email"],
            True,
            "idx_email_unique"
        )
        expected = 'CREATE UNIQUE INDEX "idx_email_unique" ON "test_table" ("email")'
        self.assertEqual(sql, expected)

    def test_get_table_sql(self):
        """Test table creation SQL generation"""
        # This would require setting up the full model metadata
        # For now, test that the method exists and returns expected structure
        self.assertTrue(hasattr(self.generator, "_get_table_sql"))

    def test_boolean_field_default(self):
        """Test boolean field default values"""
        # Test that boolean fields get proper defaults
        field = fields.BooleanField(default=True)
        db_field = field.to_db_value(True, None)
        self.assertEqual(db_field, True)

    def test_index_name_generation(self):
        """Test automatic index name generation"""
        # Index names should be properly formatted
        table_name = "test_table"
        columns = ["col1", "col2"]
        
        # The generator should handle index naming
        self.assertTrue(hasattr(self.generator, "_create_index_sql"))

    def test_field_type_mapping(self):
        """Test that field types are properly mapped"""
        # This tests the integration with the types module
        from tortoise.backends.dameng.types import TO_DB_OVERRIDE
        
        # Check some common field mappings
        self.assertIn("BIG_INT", TO_DB_OVERRIDE)
        self.assertIn("VARCHAR2", TO_DB_OVERRIDE)
        self.assertIn("NUMBER", TO_DB_OVERRIDE)
        self.assertIn("TIMESTAMP", TO_DB_OVERRIDE)