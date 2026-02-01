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
