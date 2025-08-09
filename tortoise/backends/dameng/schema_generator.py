from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.fields import Field

from .types import (
    TORTOISE_TO_DM_FIELD_MAP,
    get_field_sql_with_params,
    quote_identifier,
)

if TYPE_CHECKING:
    from .client import DmClient

logger = logging.getLogger("tortoise.backends.dameng")


class DmSchemaGenerator(BaseSchemaGenerator):
    """Dameng database schema generator"""
    
    DIALECT = "dm"
    client: DmClient
    
    # Use unified type mapping
    FIELD_TYPE_MAP = TORTOISE_TO_DM_FIELD_MAP
    
    def __init__(self, client: DmClient) -> None:
        super().__init__(client)
        self._foreign_keys: List[str] = []
    
    def quote(self, name: str) -> str:
        """Quote identifier (Dameng uses double quotes)"""
        return quote_identifier(name)
    
    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        """Generate column comment SQL - Dameng uses COMMENT ON COLUMN syntax"""
        # Dameng doesn't support inline column comments in CREATE TABLE
        # Need to execute COMMENT ON COLUMN separately
        # Return empty string to avoid syntax error
        return ""
    
    def _table_comment_generator(self, table: str, comment: str) -> str:
        """Generate table comment SQL - Dameng uses COMMENT ON TABLE syntax"""
        # Dameng doesn't support inline table comments in CREATE TABLE
        # Need to execute COMMENT ON TABLE separately
        # Return empty string to avoid syntax error
        return ""
    
    def _escape_default_value(self, default: Any) -> str:
        """Escape default value - Dameng database default value handling"""
        if default is None:
            return "NULL"
        if isinstance(default, bool):
            return "1" if default else "0"
        if isinstance(default, str):
            # Escape single quotes
            escaped = default.replace("'", "''")
            return f"'{escaped}'"
        if isinstance(default, (int, float)):
            return str(default)
        # For other types, convert to string
        return f"'{str(default)}'"
    
    def _get_column_sql(self, table: str, column: dict) -> str:
        """Generate column definition SQL"""
        column_name = self.quote(column["name"])
        column_type = column["type"]
        default = column.get("default", "")
        nullable = "" if column.get("nullable", True) else " NOT NULL"
        unique = " UNIQUE" if column.get("unique", False) else ""
        primary_key = " PRIMARY KEY" if column.get("pk", False) else ""
        
        if default:
            default = f" DEFAULT {default}"
        
        return f"{column_name} {column_type}{primary_key}{unique}{nullable}{default}"
    
    def _column_type(self, field: Field) -> Optional[str]:
        """Get database column type for field - Support full type conversion"""
        field_type = field.__class__.__name__
        
        # Skip relational fields
        if field_type in [
            "ManyToManyField", "ReverseRelation", 
            "BackwardFKRelation", "BackwardOneToOneRelation"
        ]:
            return None
        
        # Special handling for foreign key fields
        if field_type in ["ForeignKeyField", "OneToOneField"]:
            related_field = getattr(field, "related_model", None)
            if related_field:
                pk_field = getattr(related_field._meta, "pk_field", None)
                if pk_field:
                    return self._column_type(pk_field)
            return "BIGINT"  # Default to BIGINT
        
        # Use type mapping function
        column_type = get_field_sql_with_params(field_type, field)
        if column_type:
            return column_type
        
        logger.warning(f"Unknown field type: {field_type}, using default VARCHAR(255)")
        return "VARCHAR(255)"
    
    def _create_table_sql(self, table: str, columns: List[dict], comment: str = "") -> str:
        """Generate CREATE TABLE SQL"""
        columns_sql = []
        for column in columns:
            columns_sql.append(self._get_column_sql(table, column))
        
        create_sql = f"CREATE TABLE {self.quote(table)} ({', '.join(columns_sql)})"
        if comment:
            create_sql += f" COMMENT = '{comment}'"
        
        return create_sql
    
    def _create_index_sql(
        self, table: str, index_name: str, columns: List[str], unique: bool = False
    ) -> str:
        """Generate CREATE INDEX SQL"""
        unique_str = "UNIQUE " if unique else ""
        columns_str = ", ".join([self.quote(col) for col in columns])
        return (
            f"CREATE {unique_str}INDEX {self.quote(index_name)} "
            f"ON {self.quote(table)} ({columns_str})"
        )
    
    def _get_index_sql(self, model, field_names: List[str], safe: bool) -> str:
        """Override base method to handle Dameng index creation"""
        # Dameng doesn't support CREATE INDEX IF NOT EXISTS syntax
        # So we need to remove IF NOT EXISTS part
        sql = super()._get_index_sql(model, field_names, safe)
        if sql and "IF NOT EXISTS" in sql:
            sql = sql.replace("IF NOT EXISTS ", "")
        return sql
    
    async def generate_schema_for_client(self, safe: bool = True) -> str:
        """Generate schema creation SQL - Complete DDL generation implementation"""
        from tortoise import Tortoise
        
        ddl_statements = []
        
        try:
            # Get all models
            for app_name, models in Tortoise.apps.items():
                for model_name, model_cls in models.items():
                    if hasattr(model_cls, "_meta"):
                        table_name = model_cls._meta.db_table
                        
                        # Generate table structure
                        columns = []
                        indexes = []
                        foreign_keys = []
                        
                        # Process fields
                        for field_name, field_obj in model_cls._meta.fields_map.items():
                            if field_obj.__class__.__name__ in [
                                "ManyToManyField",
                                "ReverseRelation",
                                "BackwardFKRelation",
                                "BackwardOneToOneRelation",
                            ]:
                                continue
                            
                            column_type = self._column_type(field_obj)
                            if not column_type:
                                continue
                            
                            # Build column definition
                            column_def = {
                                "name": (
                                    field_obj.model_field_name 
                                    if hasattr(field_obj, "model_field_name") 
                                    else field_name
                                ),
                                "type": column_type,
                                "pk": field_obj.pk if hasattr(field_obj, "pk") else False,
                                "nullable": field_obj.null if hasattr(field_obj, "null") else True,
                                "unique": (
                                    field_obj.unique if hasattr(field_obj, "unique") else False
                                ),
                                "default": getattr(field_obj, "default", None),
                            }
                            
                            columns.append(column_def)
                            
                            # Handle indexes
                            if hasattr(field_obj, "index") and field_obj.index:
                                indexes.append({
                                    "name": f"idx_{table_name}_{field_name}",
                                    "columns": [field_name],
                                    "unique": False
                                })
                            
                            # Handle foreign keys
                            if field_obj.__class__.__name__ in ["ForeignKeyField", "OneToOneField"]:
                                related_model = field_obj.related_model
                                if related_model:
                                    foreign_keys.append({
                                        "name": f"fk_{table_name}_{field_name}",
                                        "column": field_name,
                                        "reference_table": related_model._meta.db_table,
                                        "reference_column": "id",  # Assume primary key is id
                                    })
                        
                        # Generate CREATE TABLE statement
                        if columns:
                            table_sql = self._create_table_sql(table_name, columns)
                            ddl_statements.append(table_sql)
                            
                            # Generate index statements
                            for index in indexes:
                                index_sql = self._create_index_sql(
                                    table_name, index["name"], 
                                    index["columns"], index["unique"]
                                )
                                ddl_statements.append(index_sql)
                            
                            # Generate foreign key constraint statements
                            for fk in foreign_keys:
                                fk_sql = (
                                    f"ALTER TABLE {self.quote(table_name)} "
                                    f"ADD CONSTRAINT {self.quote(fk['name'])} "
                                    f"FOREIGN KEY ({self.quote(fk['column'])}) "
                                    f"REFERENCES {self.quote(fk['reference_table'])}"
                                    f"({self.quote(fk['reference_column'])})"
                                )
                                ddl_statements.append(fk_sql)
            
            return ";\n".join(ddl_statements) + ";" if ddl_statements else ""
            
        except Exception as e:
            logger.error(f"Failed to generate database schema: {e}")
            if not safe:
                raise
            return ""