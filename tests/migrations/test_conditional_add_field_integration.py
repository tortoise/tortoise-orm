"""Integration tests for conditional migration operations."""

from __future__ import annotations

import os

import pytest

from tortoise import fields
from tortoise.contrib.test import tortoise_test_context
from tortoise.migrations.operations import AddField, CreateModel
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


class ExistingColumnWidget(Model):
    id = fields.IntField(pk=True)

    class Meta:
        app = "models"
        table = "conditional_widget"


@pytest.fixture
def postgres_db_url() -> str:
    db_url = os.getenv("TORTOISE_TEST_DB", "")
    if not db_url.startswith(("postgres://", "asyncpg://", "psycopg://")):
        pytest.skip("Requires a PostgreSQL test database")
    return db_url


def create_migration_state() -> State:
    state = State(models={}, apps=StateApps())

    CreateModel(
        name="Widget",
        fields=[("id", fields.IntField(pk=True))],
        options={"table": "conditional_widget"},
    ).state_forward("models", state)

    return state


@pytest.mark.asyncio
async def test_add_new_column_postgres(postgres_db_url: str) -> None:
    async with tortoise_test_context([__name__], db_url=postgres_db_url) as ctx:
        client = ctx.db()
        editor = BasePostgresSchemaEditor(client)
        state = create_migration_state()

        op = AddField(
            model_name="Widget",
            name="name",
            field=fields.TextField(),
            if_not_exists=True,
        )

        await op.run("models", state, dry_run=False, state_editor=editor)

        columns = await client.execute_query_dict(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = 'conditional_widget' "
            "AND column_name = 'name'"
        )

        assert len(columns) == 1
        assert columns[0]["column_name"] == "name"


@pytest.mark.asyncio
async def test_add_existing_column_postgres(postgres_db_url: str) -> None:
    async with tortoise_test_context([__name__], db_url=postgres_db_url) as ctx:
        client = ctx.db()
        editor = BasePostgresSchemaEditor(client)

        # Simulate a column that already exists in the database.
        await client.execute_query(
            'ALTER TABLE "conditional_widget" ADD COLUMN "name" TEXT NOT NULL'
        )

        state = create_migration_state()

        op = AddField(
            model_name="Widget",
            name="name",
            field=fields.TextField(),
            if_not_exists=True,
        )

        # Should succeed without adding a duplicate column.
        await op.run("models", state, dry_run=False, state_editor=editor)

        columns = await client.execute_query_dict(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = 'conditional_widget' "
            "AND column_name = 'name'"
        )

        assert len(columns) == 1
        assert columns[0]["column_name"] == "name"


@pytest.mark.asyncio
async def test_add_existing_column_postgres_without_if_not_exists(
    postgres_db_url: str,
) -> None:
    async with tortoise_test_context([__name__], db_url=postgres_db_url) as ctx:
        client = ctx.db()
        editor = BasePostgresSchemaEditor(client)

        await client.execute_query(
            'ALTER TABLE "conditional_widget" ADD COLUMN "name" TEXT NOT NULL'
        )

        state = create_migration_state()

        op = AddField(
            model_name="Widget",
            name="name",
            field=fields.TextField(),
        )

        with pytest.raises(Exception, match=r'column "name".*already exists'):
            await op.run("models", state, dry_run=False, state_editor=editor)
