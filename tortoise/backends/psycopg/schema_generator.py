from typing import TYPE_CHECKING

from tortoise.backends.base_postgres.schema_generator import \
    BasePostgresSchemaGenerator

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.asyncpg.client import PsycopgDBClient


class PsycopgSchemaGenerator(BasePostgresSchemaGenerator):

    def __init__(self, client: "PsycopgDBClient") -> None:
        super().__init__(client)
