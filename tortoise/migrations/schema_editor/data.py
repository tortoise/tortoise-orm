from dataclasses import dataclass
from typing import Type, List, Set

from tortoise.models import Model


@dataclass
class ModelSqlData:
    table: str
    model: Type[Model]
    table_sql: str
    references: Set[str]
    m2m_tables_sql: List[str]
