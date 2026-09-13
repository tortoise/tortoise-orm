from __future__ import annotations

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    Capabilities,
    ConnectionWrapper,
    TransactionContext,
)


class FakeClient(BaseDBAsyncClient):
    def __init__(
        self, dialect: str, *, inline_comment: bool = True, charset: str | None = None
    ) -> None:
        super().__init__("default")
        self.capabilities = Capabilities(dialect, inline_comment=inline_comment)
        self.charset = charset
        self.executed: list[str] = []

    async def create_connection(self, with_db: bool) -> None:
        raise NotImplementedError()

    async def close(self) -> None:
        raise NotImplementedError()

    async def db_create(self) -> None:
        raise NotImplementedError()

    async def db_delete(self) -> None:
        raise NotImplementedError()

    def acquire_connection(self) -> ConnectionWrapper:
        raise NotImplementedError()

    def _in_transaction(self) -> TransactionContext:
        raise NotImplementedError()

    async def execute_insert(self, query: str, values: list) -> int:
        raise NotImplementedError()

    async def execute_query(self, query: str, values: list | None = None) -> tuple[int, list[dict]]:
        raise NotImplementedError()

    async def execute_script(self, query: str) -> None:
        self.executed.append(query)

    async def execute_many(self, query: str, values: list[list]) -> None:
        raise NotImplementedError()

    async def execute_query_dict(self, query: str, values: list | None = None) -> list[dict]:
        raise NotImplementedError()


class MockIntrospectionClient(FakeClient):
    """A FakeClient subclass that returns configurable results for introspection queries.

    When ``execute_query`` is called with a query containing known introspection
    keywords (``pg_constraint``, ``information_schema``, ``PRAGMA index_list``,
    ``PRAGMA index_info``), the client returns configured results instead of
    raising ``NotImplementedError``.
    """

    def __init__(
        self,
        dialect: str,
        *,
        constraint_names: list[dict] | None = None,
        pragma_index_list: list[dict] | None = None,
        pragma_index_info: dict[str, list[dict]] | None = None,
        inline_comment: bool = True,
        charset: str | None = None,
    ) -> None:
        super().__init__(dialect, inline_comment=inline_comment, charset=charset)
        self.constraint_names = constraint_names or []
        self.pragma_index_list = pragma_index_list or []
        self.pragma_index_info = pragma_index_info or {}

    async def execute_query(self, query: str, values: list | None = None) -> tuple[int, list[dict]]:
        if (
            "pg_constraint" in query
            or "information_schema" in query
            or "sys.key_constraints" in query
            or "USER_CONSTRAINTS" in query
            or "ALL_CONSTRAINTS" in query
        ):
            return len(self.constraint_names), self.constraint_names
        if "PRAGMA index_list" in query:
            return len(self.pragma_index_list), self.pragma_index_list
        if "PRAGMA index_info" in query:
            # Extract the index name from the query: PRAGMA index_info("idx_name")
            idx_name = query.split('"')[1] if '"' in query else ""
            info = self.pragma_index_info.get(idx_name, [])
            return len(info), info
        raise NotImplementedError()
