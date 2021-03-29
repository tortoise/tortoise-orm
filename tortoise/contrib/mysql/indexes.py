from tortoise.indexes import Index


class FullTextIndex(Index):
    INDEX_CREATE_TEMPLATE = "CREATE FULLTEXT INDEX `{index_name}` ON `{table_name}` ({fields});"
