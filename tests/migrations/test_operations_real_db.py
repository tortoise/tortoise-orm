"""Integration tests: Tortoise migration operations executed via schema editors on real databases.

These tests verify that migration operations (CreateModel, AddField, AlterField,
AddConstraint, RemoveConstraint, etc.) work end-to-end when executed through
their backend-specific schema editors against a real database.

All tests use the ``db_isolated`` fixture for full per-test database isolation.
Each test:
  1. Builds migration state (ModelState / State / StateApps)
  2. Instantiates the correct backend SchemaEditor via the executor factory
  3. Calls ``operation.run(app_label, state, dry_run=False, state_editor=editor)``
  4. Verifies the database state via raw SQL queries
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tortoise.fields.data import CharField, DatetimeField, IntField
from tortoise.fields.db_defaults import Now
from tortoise.migrations.constraints import CheckConstraint, UniqueConstraint
from tortoise.migrations.operations import (
    AddConstraint,
    AddField,
    AlterField,
    CreateModel,
    DeleteModel,
    RemoveConstraint,
    RemoveField,
    RenameModel,
)
from tortoise.migrations.schema_generator.state import State, StateApps

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_schema_editor(conn):
    """Get the correct backend-specific SchemaEditor for the given connection.

    Mirrors the factory logic in MigrationExecutor._schema_editor().
    """
    from tortoise.migrations.schema_editor import (
        AsyncpgSchemaEditor,
        BasePostgresSchemaEditor,
        BaseSchemaEditor,
        MSSQLSchemaEditor,
        MySQLSchemaEditor,
        OracleSchemaEditor,
        PsycopgSchemaEditor,
        SqliteSchemaEditor,
    )

    module = conn.__class__.__module__
    dialect = conn.capabilities.dialect
    if "sqlite" in module:
        return SqliteSchemaEditor(conn, atomic=True, collect_sql=False)
    if "asyncpg" in module:
        return AsyncpgSchemaEditor(conn, atomic=True, collect_sql=False)
    if "psycopg" in module:
        return PsycopgSchemaEditor(conn, atomic=True, collect_sql=False)
    if "mysql" in module:
        return MySQLSchemaEditor(conn, atomic=True, collect_sql=False)
    if "mssql" in module or "odbc" in module:
        return MSSQLSchemaEditor(conn, atomic=True, collect_sql=False)
    if "oracle" in module:
        return OracleSchemaEditor(conn, atomic=True, collect_sql=False)
    if dialect == "postgres":
        return BasePostgresSchemaEditor(conn, atomic=True, collect_sql=False)
    return BaseSchemaEditor(conn, atomic=True, collect_sql=False)


def q(name: str, dialect: str) -> str:
    """Quote an identifier for the given dialect."""
    if dialect == "mysql":
        return f"`{name}`"
    if dialect == "mssql":
        return f"[{name}]"
    return f'"{name}"'


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_model_and_delete_model(db_isolated):
    """CreateModel creates a real table; DeleteModel drops it."""
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect
    editor = _get_schema_editor(conn)

    create_op = CreateModel(
        name="Widget",
        fields=[
            ("id", IntField(primary_key=True)),
            ("name", CharField(max_length=100)),
        ],
        options={"table": "test_widget"},
    )
    state = State(models={}, apps=StateApps())

    try:
        # Forward: create the table
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        # Verify table exists by inserting and querying (let auto-increment assign id)
        tbl = q("test_widget", dialect)
        await conn.execute_script(f"INSERT INTO {tbl} ({q('name', dialect)}) VALUES ('gizmo')")
        rows = await conn.execute_query_dict(f"SELECT * FROM {tbl}")
        assert len(rows) == 1
        assert rows[0]["name"] == "gizmo"

        # Backward: delete the table
        delete_op = DeleteModel(name="Widget")
        await delete_op.run("models", state, dry_run=False, state_editor=editor)

        # Verify table no longer exists
        with pytest.raises(Exception):
            await conn.execute_query_dict(f"SELECT * FROM {tbl}")
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_widget', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_add_field_with_db_default(db_isolated):
    """AddField with db_default=42 creates a column whose default is applied on INSERT."""
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect
    editor = _get_schema_editor(conn)

    # Step 1: Create the table via CreateModel
    create_op = CreateModel(
        name="Product",
        fields=[
            ("id", IntField(primary_key=True)),
            ("name", CharField(max_length=100)),
        ],
        options={"table": "test_product"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        # Step 2: Add a field with db_default via AddField
        add_op = AddField(
            model_name="Product",
            name="stock",
            field=IntField(null=False, db_default=42),
        )
        await add_op.run("models", state, dry_run=False, state_editor=editor)

        # Step 3: Insert without specifying stock — should get default
        tbl = q("test_product", dialect)
        await conn.execute_script(f"INSERT INTO {tbl} ({q('name', dialect)}) VALUES ('widget')")

        rows = await conn.execute_query_dict(f"SELECT * FROM {tbl}")
        assert len(rows) == 1
        assert rows[0]["stock"] == 42
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_product', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_add_field_with_now_default(db_isolated):
    """AddField with db_default=Now() creates a timestamp column with a server-side default."""
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect
    editor = _get_schema_editor(conn)

    create_op = CreateModel(
        name="Event",
        fields=[
            ("id", IntField(primary_key=True)),
            ("title", CharField(max_length=100)),
        ],
        options={"table": "test_event"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        # Add a datetime field with Now() default
        add_op = AddField(
            model_name="Event",
            name="created_at",
            field=DatetimeField(null=True, db_default=Now()),
        )
        await add_op.run("models", state, dry_run=False, state_editor=editor)

        before = datetime.now(timezone.utc)

        tbl = q("test_event", dialect)
        await conn.execute_script(f"INSERT INTO {tbl} ({q('title', dialect)}) VALUES ('launch')")

        after = datetime.now(timezone.utc)

        rows = await conn.execute_query_dict(f"SELECT * FROM {tbl}")
        assert len(rows) == 1
        raw_value = rows[0]["created_at"]
        assert raw_value is not None, "Now() default should populate the timestamp"

        # Parse and verify the timestamp is recent
        if isinstance(raw_value, str):
            ts = (
                datetime.fromisoformat(raw_value)
                if "T" in raw_value
                else datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")
            )
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        elif isinstance(raw_value, datetime):
            ts = raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=timezone.utc)
        else:
            pytest.fail(f"Unexpected timestamp type: {type(raw_value)}")

        assert (ts - before).total_seconds() >= -2
        assert (after - ts).total_seconds() >= -2
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_event', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_alter_field_set_and_drop_db_default(db_isolated):
    """AlterField can SET DEFAULT and then DROP DEFAULT on a real database.

    The table is created without a db_default, then AlterField is used to
    add and subsequently remove the default — this is purely testing the
    AlterField SET/DROP DEFAULT code path.
    """
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect

    if dialect == "sqlite":
        pytest.skip("SQLite does not support ALTER COLUMN SET/DROP DEFAULT")

    editor = _get_schema_editor(conn)

    # Create table WITHOUT db_default — the column is nullable so inserts
    # without a value succeed even before a default is set.
    # A "tag" column is used to distinguish rows instead of explicit id values,
    # so that auto-increment / IDENTITY works on every backend.
    create_op = CreateModel(
        name="Setting",
        fields=[
            ("id", IntField(primary_key=True)),
            ("tag", CharField(max_length=50)),
            ("value", IntField(null=True)),
        ],
        options={"table": "test_setting"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        tbl = q("test_setting", dialect)

        # AlterField: set default to 99
        alter_op = AlterField(
            model_name="Setting",
            name="value",
            field=IntField(null=True, db_default=99),
        )
        await alter_op.run("models", state, dry_run=False, state_editor=editor)

        # Insert without specifying value — should get default 99
        await conn.execute_script(
            f"INSERT INTO {tbl} ({q('tag', dialect)}) VALUES ('with_default')"
        )
        rows = await conn.execute_query_dict(
            f"SELECT * FROM {tbl} WHERE {q('tag', dialect)} = 'with_default'"
        )
        assert rows[0]["value"] == 99

        # AlterField: drop default
        drop_op = AlterField(
            model_name="Setting",
            name="value",
            field=IntField(null=True),
        )
        await drop_op.run("models", state, dry_run=False, state_editor=editor)

        # Insert with explicit NULL for value — verifies default no longer applies.
        # We use explicit NULL rather than omitting the column because MySQL in
        # strict mode rejects omitted nullable columns after DROP DEFAULT.
        await conn.execute_script(
            f"INSERT INTO {tbl} ({q('tag', dialect)}, {q('value', dialect)}) VALUES ('no_default', NULL)"
        )
        rows = await conn.execute_query_dict(
            f"SELECT * FROM {tbl} WHERE {q('tag', dialect)} = 'no_default'"
        )
        assert rows[0]["value"] is None
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_setting', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_remove_field(db_isolated):
    """RemoveField drops a column from a real table."""
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect

    if dialect == "sqlite":
        pytest.skip("SQLite does not support DROP COLUMN in older versions")

    editor = _get_schema_editor(conn)

    create_op = CreateModel(
        name="Article",
        fields=[
            ("id", IntField(primary_key=True)),
            ("title", CharField(max_length=200)),
            ("subtitle", CharField(max_length=200)),
        ],
        options={"table": "test_article"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        # Verify column exists
        tbl = q("test_article", dialect)
        await conn.execute_script(
            f"INSERT INTO {tbl} ({q('title', dialect)}, {q('subtitle', dialect)}) "
            f"VALUES ('Hello', 'World')"
        )

        # Remove the subtitle field
        remove_op = RemoveField(model_name="Article", name="subtitle")
        await remove_op.run("models", state, dry_run=False, state_editor=editor)

        # Verify column is gone — querying it should fail
        with pytest.raises(Exception):
            await conn.execute_query_dict(f"SELECT {q('subtitle', dialect)} FROM {tbl}")

        # But the table and other columns still work
        rows = await conn.execute_query_dict(f"SELECT {q('title', dialect)} FROM {tbl}")
        assert len(rows) == 1
        assert rows[0]["title"] == "Hello"
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_article', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_rename_model(db_isolated):
    """RenameModel renames a table in the real database.

    Uses default table names (lowercased model name) because RenameModel only
    renames the underlying table when the table name matches the default
    convention (old_name.lower() -> new_name.lower()).  Custom table names are
    intentionally left unchanged by the operation.
    """
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect
    editor = _get_schema_editor(conn)

    # Use default table naming (lowercased model name, no custom table option)
    create_op = CreateModel(
        name="OldName",
        fields=[
            ("id", IntField(primary_key=True)),
            ("value", IntField(null=False, default=0)),
        ],
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        # Insert data under old name (default table = "oldname")
        old_tbl = q("oldname", dialect)
        await conn.execute_script(f"INSERT INTO {old_tbl} ({q('value', dialect)}) VALUES (42)")

        # Rename: table should change from "oldname" to "newname"
        rename_op = RenameModel(old_name="OldName", new_name="NewName")
        await rename_op.run("models", state, dry_run=False, state_editor=editor)

        # Query via new table name
        new_tbl = q("newname", dialect)
        rows = await conn.execute_query_dict(f"SELECT * FROM {new_tbl}")
        assert len(rows) == 1
        assert rows[0]["value"] == 42

        # Old table name should not exist
        with pytest.raises(Exception):
            await conn.execute_query_dict(f"SELECT * FROM {old_tbl}")
    finally:
        for tbl_name in ("oldname", "newname"):
            try:
                await conn.execute_script(f"DROP TABLE IF EXISTS {q(tbl_name, dialect)}")
            except Exception:
                pass


@pytest.mark.asyncio
async def test_add_and_remove_unique_constraint(db_isolated):
    """AddConstraint creates a unique constraint; RemoveConstraint drops it."""
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect
    editor = _get_schema_editor(conn)

    from tortoise.exceptions import IntegrityError

    create_op = CreateModel(
        name="Employee",
        fields=[
            ("id", IntField(primary_key=True)),
            ("email", CharField(max_length=200)),
        ],
        options={"table": "test_employee"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        tbl = q("test_employee", dialect)

        # Add unique constraint via AddConstraint operation
        constraint = UniqueConstraint(fields=("email",), name="uq_employee_email")
        add_constraint_op = AddConstraint(model_name="Employee", constraint=constraint)
        await add_constraint_op.run("models", state, dry_run=False, state_editor=editor)

        # Insert first row
        await conn.execute_script(
            f"INSERT INTO {tbl} ({q('email', dialect)}) VALUES ('alice@test.com')"
        )

        # Duplicate should fail
        with pytest.raises(IntegrityError):
            await conn.execute_script(
                f"INSERT INTO {tbl} ({q('email', dialect)}) VALUES ('alice@test.com')"
            )

        # Remove the constraint
        remove_constraint_op = RemoveConstraint(model_name="Employee", name="uq_employee_email")
        await remove_constraint_op.run("models", state, dry_run=False, state_editor=editor)

        # Now duplicates should be allowed
        await conn.execute_script(
            f"INSERT INTO {tbl} ({q('email', dialect)}) VALUES ('alice@test.com')"
        )

        rows = await conn.execute_query_dict(
            f"SELECT * FROM {tbl} WHERE {q('email', dialect)} = 'alice@test.com'"
        )
        assert len(rows) == 2
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_employee', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_add_check_constraint(db_isolated):
    """AddConstraint with CheckConstraint enforces data validation on real DB."""
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect

    if dialect == "mysql":
        pytest.skip("MySQL CHECK constraint enforcement varies by version")

    editor = _get_schema_editor(conn)

    from tortoise.exceptions import IntegrityError, OperationalError

    create_op = CreateModel(
        name="Product",
        fields=[
            ("id", IntField(primary_key=True)),
            ("price", IntField(null=False)),
        ],
        options={"table": "test_product_ck"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        # Add check constraint
        constraint = CheckConstraint(check="price > 0", name="ck_product_price_positive")
        add_op = AddConstraint(model_name="Product", constraint=constraint)
        await add_op.run("models", state, dry_run=False, state_editor=editor)

        tbl = q("test_product_ck", dialect)

        # Valid insert
        await conn.execute_script(f"INSERT INTO {tbl} ({q('price', dialect)}) VALUES (100)")

        # Invalid insert should be rejected
        with pytest.raises((IntegrityError, OperationalError)):
            await conn.execute_script(f"INSERT INTO {tbl} ({q('price', dialect)}) VALUES (-5)")
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_product_ck', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_alter_field_null_change(db_isolated):
    """AlterField can change a column from NOT NULL to NULL and back."""
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect

    if dialect == "sqlite":
        pytest.skip("SQLite does not support ALTER COLUMN nullability changes")

    editor = _get_schema_editor(conn)

    create_op = CreateModel(
        name="Config",
        fields=[
            ("id", IntField(primary_key=True)),
            ("value", IntField(null=False, default=0)),
        ],
        options={"table": "test_config"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        tbl = q("test_config", dialect)

        # Currently NOT NULL — inserting NULL should fail
        with pytest.raises(Exception):
            await conn.execute_script(f"INSERT INTO {tbl} ({q('value', dialect)}) VALUES (NULL)")

        # AlterField: make nullable
        alter_op = AlterField(
            model_name="Config",
            name="value",
            field=IntField(null=True),
        )
        await alter_op.run("models", state, dry_run=False, state_editor=editor)

        # Now NULL should be accepted
        await conn.execute_script(f"INSERT INTO {tbl} ({q('value', dialect)}) VALUES (NULL)")
        rows = await conn.execute_query_dict(f"SELECT * FROM {tbl}")
        # Find the row with NULL value
        null_rows = [r for r in rows if r["value"] is None]
        assert len(null_rows) == 1

        # AlterField: make NOT NULL again
        # First, update the NULL row so ALTER doesn't fail
        await conn.execute_script(
            f"UPDATE {tbl} SET {q('value', dialect)} = 0 WHERE {q('value', dialect)} IS NULL"
        )

        alter_back_op = AlterField(
            model_name="Config",
            name="value",
            field=IntField(null=False),
        )
        await alter_back_op.run("models", state, dry_run=False, state_editor=editor)

        # NULL should be rejected again
        with pytest.raises(Exception):
            await conn.execute_script(f"INSERT INTO {tbl} ({q('value', dialect)}) VALUES (NULL)")
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_config', dialect)}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Issue #2141 reproduction tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alter_field_max_length_preserves_db_default(db_isolated):
    """Changing max_length on a field with db_default must not lose the default.

    Reproduces https://github.com/tortoise/tortoise-orm/issues/2141 (bug 1).

    On MySQL, MODIFY COLUMN resets the full column definition.  If the
    migration editor only emits ``MODIFY COLUMN col VARCHAR(20) NOT NULL``
    without re-applying the DEFAULT, the database default silently disappears.
    """
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect

    if dialect == "sqlite":
        pytest.skip("SQLite uses table-recreation, not ALTER COLUMN")

    editor = _get_schema_editor(conn)

    # Create table with a VARCHAR(10) column that has db_default=''
    create_op = CreateModel(
        name="Profile",
        fields=[
            ("id", IntField(primary_key=True)),
            ("tag", CharField(max_length=50)),
            ("name", CharField(max_length=10, db_default="")),
        ],
        options={"table": "test_profile_2141"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        tbl = q("test_profile_2141", dialect)

        # Verify the default works before any ALTER
        await conn.execute_script(
            f"INSERT INTO {tbl} ({q('tag', dialect)}) VALUES ('before_alter')"
        )
        rows = await conn.execute_query_dict(
            f"SELECT * FROM {tbl} WHERE {q('tag', dialect)} = 'before_alter'"
        )
        assert rows[0]["name"] == "", "db_default='' should produce empty string"

        # AlterField: change max_length from 10 -> 20, keeping db_default=''
        alter_op = AlterField(
            model_name="Profile",
            name="name",
            field=CharField(max_length=20, db_default=""),
        )
        await alter_op.run("models", state, dry_run=False, state_editor=editor)

        # Insert again omitting 'name' — the default should still work
        await conn.execute_script(f"INSERT INTO {tbl} ({q('tag', dialect)}) VALUES ('after_alter')")
        rows = await conn.execute_query_dict(
            f"SELECT * FROM {tbl} WHERE {q('tag', dialect)} = 'after_alter'"
        )
        assert rows[0]["name"] == "", "db_default='' was lost after AlterField changed max_length"
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_profile_2141', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_alter_field_null_change_preserves_db_default(db_isolated):
    """Changing nullability on a field with db_default must not lose the default.

    Reproduces a variant of https://github.com/tortoise/tortoise-orm/issues/2141
    (bug 1) where the trigger is a nullability change instead of max_length.
    """
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect

    if dialect == "sqlite":
        pytest.skip("SQLite uses table-recreation, not ALTER COLUMN")

    editor = _get_schema_editor(conn)

    # Create table with db_default=99 on an integer column
    create_op = CreateModel(
        name="Score",
        fields=[
            ("id", IntField(primary_key=True)),
            ("tag", CharField(max_length=50)),
            ("value", IntField(null=False, db_default=99)),
        ],
        options={"table": "test_score_2141"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        tbl = q("test_score_2141", dialect)

        # Verify the default works before any ALTER
        await conn.execute_script(f"INSERT INTO {tbl} ({q('tag', dialect)}) VALUES ('before')")
        rows = await conn.execute_query_dict(
            f"SELECT * FROM {tbl} WHERE {q('tag', dialect)} = 'before'"
        )
        assert rows[0]["value"] == 99

        # AlterField: make nullable, keep same db_default
        alter_op = AlterField(
            model_name="Score",
            name="value",
            field=IntField(null=True, db_default=99),
        )
        await alter_op.run("models", state, dry_run=False, state_editor=editor)

        # The default should still work after the null change
        await conn.execute_script(f"INSERT INTO {tbl} ({q('tag', dialect)}) VALUES ('after_null')")
        rows = await conn.execute_query_dict(
            f"SELECT * FROM {tbl} WHERE {q('tag', dialect)} = 'after_null'"
        )
        assert rows[0]["value"] == 99, "db_default=99 was lost after AlterField changed nullability"
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_score_2141', dialect)}")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_alter_field_description_change_applied(db_isolated):
    """Changing only a field's description should execute actual DDL.

    Reproduces https://github.com/tortoise/tortoise-orm/issues/2141 (bug 2).

    The migration diff detects description changes (migration file IS created),
    but ``_alter_field`` has ``pass`` for description changes, so no SQL runs.
    On PostgreSQL this should emit ``COMMENT ON COLUMN``; on MySQL the COMMENT
    should appear in a ``MODIFY COLUMN`` clause.
    """
    conn = db_isolated.db()
    dialect = conn.capabilities.dialect

    if dialect == "sqlite":
        pytest.skip("SQLite does not support column comments")

    editor = _get_schema_editor(conn)

    create_op = CreateModel(
        name="Item",
        fields=[
            ("id", IntField(primary_key=True)),
            ("name", CharField(max_length=100, description="item name")),
        ],
        options={"table": "test_item_2141"},
    )
    state = State(models={}, apps=StateApps())

    try:
        await create_op.run("models", state, dry_run=False, state_editor=editor)

        # AlterField: change only the description
        alter_op = AlterField(
            model_name="Item",
            name="name",
            field=CharField(max_length=100, description="short item name"),
        )
        await alter_op.run("models", state, dry_run=False, state_editor=editor)

        # Verify the comment was actually updated in the database
        tbl = "test_item_2141"
        if dialect in ("postgres",):
            query = (
                "SELECT col_description(c.oid, a.attnum) AS comment "
                "FROM pg_class c "
                "JOIN pg_attribute a ON a.attrelid = c.oid "
                f"WHERE c.relname = '{tbl}' AND a.attname = 'name'"
            )
            rows = await conn.execute_query_dict(query)
            comment = rows[0]["comment"] if rows else None
            assert comment == "short item name", (
                f"PostgreSQL column comment not updated: got {comment!r}"
            )
        elif dialect == "mysql":
            query = (
                "SELECT COLUMN_COMMENT FROM INFORMATION_SCHEMA.COLUMNS "
                f"WHERE TABLE_NAME = '{tbl}' AND COLUMN_NAME = 'name'"
            )
            rows = await conn.execute_query_dict(query)
            comment = rows[0]["COLUMN_COMMENT"] if rows else None
            assert comment == "short item name", (
                f"MySQL column comment not updated: got {comment!r}"
            )
        else:
            pytest.skip(f"Comment introspection not implemented for {dialect}")
    finally:
        try:
            await conn.execute_script(f"DROP TABLE IF EXISTS {q('test_item_2141', dialect)}")
        except Exception:
            pass
