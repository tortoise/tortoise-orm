from typing import Optional, Set

from pypika.terms import Term, ValueWrapper

from tortoise.indexes import Index


class PostgreSQLIndex(Index):
    INDEX_CREATE_TEMPLATE = (
        "CREATE INDEX {exists}{index_name} ON {table_name} USING{index_type}({fields}){extra};"
    )

    def __init__(
        self,
        *expressions: Term,
        fields: Optional[Set[str]] = None,
        name: Optional[str] = None,
        condition: Optional[dict] = None,
    ):
        super().__init__(*expressions, fields=fields, name=name)
        if condition:
            cond = " WHERE "
            items = []
            for k, v in condition.items():
                items.append(f"{k} = {ValueWrapper(v)}")
            cond += " AND ".join(items)
            self.extra = cond


class BloomIndex(PostgreSQLIndex):
    INDEX_TYPE = "BLOOM"


class BrinIndex(PostgreSQLIndex):
    INDEX_TYPE = "BRIN"


class GinIndex(PostgreSQLIndex):
    INDEX_TYPE = "GIN"


class GistIndex(PostgreSQLIndex):
    INDEX_TYPE = "GIST"


class HashIndex(PostgreSQLIndex):
    INDEX_TYPE = "HASH"


class SpGistIndex(PostgreSQLIndex):
    INDEX_TYPE = "SPGIST"
