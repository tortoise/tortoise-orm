from abc import ABCMeta

from tortoise.indexes import Index


class PostgreSQLIndex(Index, metaclass=ABCMeta):
    INDEX_CREATE_TEMPLATE = "CREATE INDEX {index_name} ON {table_name} USING{index_type}({fields});"


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
