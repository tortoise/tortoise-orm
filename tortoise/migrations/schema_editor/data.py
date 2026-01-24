from __future__ import annotations

from dataclasses import dataclass

from tortoise.models import Model


@dataclass
class ModelSqlData:
    table: str
    model: type[Model]
    table_sql: str
    references: set[str]
    m2m_tables_sql: list[str]
