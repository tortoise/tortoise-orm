from __future__ import annotations


class SqlDefault:
    """Represents a raw SQL expression for use as a database-level default value.

    Use this with the ``db_default`` parameter on fields to emit raw SQL
    in both ``generate_schemas()`` and migrations.

    .. warning::
        The SQL string is emitted verbatim into DDL statements.
        Never construct it from untrusted user input.

    Example::

        class MyModel(Model):
            created_at = fields.DatetimeField(db_default=SqlDefault("CURRENT_TIMESTAMP"))
    """

    def __init__(self, sql: str) -> None:
        self.sql = sql

    def get_sql(self, _context=None, dialect: str | None = None) -> str:
        return self.sql

    def __repr__(self) -> str:
        return f"SqlDefault({self.sql!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SqlDefault) and self.sql == other.sql

    def __hash__(self) -> int:
        return hash(self.sql)


class Now(SqlDefault):
    """Convenience subclass of :class:`SqlDefault` that emits ``CURRENT_TIMESTAMP``.

    Example::

        class MyModel(Model):
            created_at = fields.DatetimeField(db_default=Now())
    """

    _DIALECT_SQL: dict[str, str] = {
        "mysql": "CURRENT_TIMESTAMP(6)",
    }

    def __init__(self) -> None:
        super().__init__("CURRENT_TIMESTAMP")

    def get_sql(self, _context=None, dialect: str | None = None) -> str:
        if dialect and dialect in self._DIALECT_SQL:
            return self._DIALECT_SQL[dialect]
        return self.sql

    def __repr__(self) -> str:
        return "Now()"


class RandomHex(SqlDefault):
    """Convenience subclass of :class:`SqlDefault` that emits a dialect-specific
    expression for generating a random 32-character hex string.

    Example::

        class MyModel(Model):
            tracking_id = fields.CharField(max_length=36, db_default=RandomHex())
    """

    _DIALECT_SQL: dict[str, str] = {
        "sqlite": "(lower(hex(randomblob(16))))",
        "postgres": "md5(random()::text)",
        "mysql": "(LOWER(HEX(RANDOM_BYTES(16))))",
        "mssql": "(LOWER(CONVERT(VARCHAR(32), HASHBYTES('MD5', NEWID()), 2)))",
        "oracle": "LOWER(RAWTOHEX(SYS_GUID()))",
    }

    def __init__(self) -> None:
        super().__init__(self._DIALECT_SQL["sqlite"])

    def get_sql(self, _context=None, dialect: str | None = None) -> str:
        if dialect and dialect in self._DIALECT_SQL:
            return self._DIALECT_SQL[dialect]
        return self.sql

    def __repr__(self) -> str:
        return "RandomHex()"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RandomHex)

    def __hash__(self) -> int:
        return hash("RandomHex")
