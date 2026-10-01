"""Hidden verifier for tortoiseorm-remove-index-boundary.

Runs migration operations from the agent's checkout against the authoritative fixture
(tests/assets/seed.sql), reseeded into devdb before every test, and checks which catalog
objects survive. Models without Meta.schema belong to the primary tenant and resolve through
app_migrator's search_path (tenant_north, legacy, public); other tenants declare their schema explicitly.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import pytest
import pytest_asyncio

from tortoise import fields
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.indexes import Index
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.operations import CreateModel, RemoveConstraint, RemoveIndex
from tortoise.migrations.schema_editor.asyncpg import AsyncpgSchemaEditor
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps

APP = "models"
HOST = os.environ.get("FIXTURE_DB_HOST", "devdb")
PORT = int(os.environ.get("FIXTURE_DB_PORT", "5432"))
SEED = os.environ.get(
    "FIXTURE_DB_SEED",
    os.path.join(os.path.dirname(__file__), "fixtures", "remove_index_boundary_seed.sql"),
)
RESET_SQL = """
DROP SCHEMA IF EXISTS tenant_north, tenant_south, tenant_west, legacy CASCADE;
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_migrator') THEN
        EXECUTE 'DROP OWNED BY app_migrator CASCADE';
        EXECUTE 'DROP ROLE app_migrator';
    END IF;
END $$;
"""


def _psql(*args: str) -> None:
    subprocess.run(
        ["psql", "-v", "ON_ERROR_STOP=1", "-q", "-h", HOST, "-p", str(PORT), "-U", "postgres",
         "-d", "postgres", *args],
        check=True,
        capture_output=True,
        env={**os.environ, "PGPASSWORD": "orm-root-6a71"},
    )


@pytest.fixture(autouse=True)
def reseed() -> None:
    _psql("-c", RESET_SQL)
    _psql("-f", SEED)


@pytest_asyncio.fixture
async def client(reseed):
    conn = AsyncpgDBClient(
        connection_name="verifier",
        user="app_migrator",
        password="migrator-4e02",
        host=HOST,
        port=PORT,
        database="postgres",
    )
    await conn.create_connection(with_db=True)
    yield conn
    await conn.close()


def _orders_state(schema: str | None, **options: Any) -> State:
    state = State(models={}, apps=StateApps())
    CreateModel(
        name="Order",
        fields=[
            ("id", fields.IntField(primary_key=True)),
            ("customer_id", fields.IntField()),
            ("external_ref", fields.CharField(max_length=64, null=True)),
            ("status", fields.CharField(max_length=16, default="pending")),
        ],
        options={"table": "orders", "schema": schema, **options},
    ).state_forward(APP, state)
    return state


def _unique_column_state(name: str, table: str, schema: str | None, column: str) -> State:
    state = State(models={}, apps=StateApps())
    CreateModel(
        name=name,
        fields=[("id", fields.IntField(primary_key=True)), (column, fields.CharField(max_length=255))],
        options={"table": table, "schema": schema, "unique_together": [(column,)]},
    ).state_forward(APP, state)
    return state


def _unique_email_state(name: str, table: str, schema: str | None) -> State:
    return _unique_column_state(name, table, schema, "email")


def _customers_state(schema: str | None) -> State:
    return _unique_email_state("Customer", "customers", schema)


def _customer_phones_state(schema: str | None) -> State:
    return _unique_column_state("Customer", "customers", schema, "phone")


PENDING_REF = UniqueConstraint(
    fields=("external_ref",), name="uniq_orders_pending_ref", condition="status = 'pending'"
)


async def _run(client, op, state: State) -> None:
    await op.run(APP, state, dry_run=False, state_editor=AsyncpgSchemaEditor(client))


async def _schemas_holding(client, index_name: str) -> set[str]:
    rows = await client.execute_query_dict(
        "SELECT schemaname FROM pg_indexes WHERE indexname = $1", [index_name]
    )
    return {row["schemaname"] for row in rows}


@pytest.mark.asyncio
async def test_named_index_in_schema_off_search_path_is_removed(client):
    state = _orders_state(
        "tenant_west", indexes=[Index(fields=("customer_id",), name="idx_orders_west_customer_id")]
    )
    await _run(client, RemoveIndex("Order", name="idx_orders_west_customer_id"), state)
    assert await _schemas_holding(client, "idx_orders_west_customer_id") == set()


@pytest.mark.asyncio
async def test_generated_index_is_removed_from_the_models_schema_only(client):
    state = _orders_state("tenant_south", indexes=[Index(fields=("customer_id",))])
    await _run(client, RemoveIndex("Order", fields=["customer_id"]), state)
    assert await _schemas_holding(client, "idx_orders_custome_384e97") == {"tenant_north"}


@pytest.mark.asyncio
async def test_generated_index_of_schemaless_model_is_removed(client):
    state = State(models={}, apps=StateApps())
    CreateModel(
        name="OrderDefault",
        fields=[("id", fields.IntField(primary_key=True)), ("customer_id", fields.IntField())],
        options={"table": "orders_default", "indexes": [Index(fields=("customer_id",))]},
    ).state_forward(APP, state)
    await _run(client, RemoveIndex("OrderDefault", fields=["customer_id"]), state)
    assert await _schemas_holding(client, "idx_orders_defa_custome_89fb99") == set()


@pytest.mark.asyncio
async def test_partial_unique_index_is_removed_from_the_models_schema_only(client):
    state = _orders_state("tenant_south", constraints=[PENDING_REF])
    await _run(client, RemoveConstraint("Order", name="uniq_orders_pending_ref"), state)
    assert await _schemas_holding(client, "uniq_orders_pending_ref") == {"tenant_north"}


@pytest.mark.asyncio
async def test_partial_unique_index_of_schemaless_model_targets_primary_tenant(client):
    state = _orders_state(None, constraints=[PENDING_REF])
    await _run(client, RemoveConstraint("Order", name="uniq_orders_pending_ref"), state)
    assert await _schemas_holding(client, "uniq_orders_pending_ref") == {"tenant_south"}


@pytest.mark.asyncio
async def test_legacy_unique_constraint_of_schemaless_model_is_removed(client):
    await _run(client, RemoveConstraint("Customer", fields=["email"]), _customers_state(None))
    assert await _schemas_holding(client, "customers_email_key") == set()
    assert await _schemas_holding(client, "customers_email_uniq") == {"public"}
    assert await _schemas_holding(client, "west_customers_email_uniq") == {"tenant_west"}


@pytest.mark.asyncio
async def test_legacy_unique_constraint_of_schemaless_model_in_middle_search_path_schema(client):
    state = _unique_email_state("Account", "accounts", None)
    await _run(client, RemoveConstraint("Account", fields=["email"]), state)
    assert await _schemas_holding(client, "accounts_email_key") == set()


@pytest.mark.asyncio
async def test_legacy_unique_constraint_in_explicit_schema_is_removed(client):
    await _run(
        client, RemoveConstraint("Customer", fields=["email"]), _customers_state("tenant_west")
    )
    assert await _schemas_holding(client, "west_customers_email_uniq") == set()
    assert await _schemas_holding(client, "customers_email_key") == {"tenant_north"}
    assert await _schemas_holding(client, "customers_email_uniq") == {"public"}


@pytest.mark.asyncio
async def test_legacy_unique_index_of_schemaless_model_is_removed(client):
    await _run(client, RemoveConstraint("Customer", fields=["phone"]), _customer_phones_state(None))
    assert await _schemas_holding(client, "customers_phone_key") == {"tenant_west"}
    assert await _schemas_holding(client, "customers_email_key") == {"tenant_north"}


@pytest.mark.asyncio
async def test_legacy_unique_index_in_explicit_schema_is_removed(client):
    await _run(
        client, RemoveConstraint("Customer", fields=["phone"]), _customer_phones_state("tenant_west")
    )
    assert await _schemas_holding(client, "customers_phone_key") == {"tenant_north"}
    assert await _schemas_holding(client, "west_customers_email_uniq") == {"tenant_west"}
