from __future__ import annotations


class RawSQLTerm:
    def __init__(self, sql: str) -> None:
        self.sql = sql

    def get_sql(self, _context) -> str:
        return self.sql
