from __future__ import annotations

import pytest

from tortoise import fields
from tortoise.exceptions import ConfigurationError
from tortoise.fields.base import DB_DEFAULT_NOT_SET

# ============================================================================
# has_db_default() tests
# ============================================================================


def test_db_default_not_set():
    f = fields.IntField()
    assert f.has_db_default() is False
    assert f.db_default is DB_DEFAULT_NOT_SET


def test_db_default_set_int():
    f = fields.IntField(db_default=42)
    assert f.has_db_default() is True
    assert f.db_default == 42


def test_db_default_set_str():
    f = fields.CharField(max_length=100, db_default="hello")
    assert f.has_db_default() is True
    assert f.db_default == "hello"


def test_db_default_set_bool():
    f = fields.BooleanField(db_default=True)
    assert f.has_db_default() is True
    assert f.db_default is True


def test_db_default_set_float():
    f = fields.FloatField(db_default=3.14)
    assert f.has_db_default() is True
    assert f.db_default == 3.14


def test_db_default_set_none():
    """None is a valid db_default (maps to DEFAULT NULL)."""
    f = fields.IntField(null=True, db_default=None)
    assert f.has_db_default() is True
    assert f.db_default is None


def test_db_default_set_zero():
    """0 is a valid db_default, not to be confused with sentinel."""
    f = fields.IntField(db_default=0)
    assert f.has_db_default() is True
    assert f.db_default == 0


def test_db_default_set_empty_string():
    f = fields.CharField(max_length=100, db_default="")
    assert f.has_db_default() is True
    assert f.db_default == ""


def test_db_default_set_false():
    f = fields.BooleanField(db_default=False)
    assert f.has_db_default() is True
    assert f.db_default is False


# ============================================================================
# Callable db_default raises ConfigurationError
# ============================================================================


def test_db_default_callable_raises():
    with pytest.raises(ConfigurationError, match="db_default must be a static value"):
        fields.IntField(db_default=lambda: 1)


def test_db_default_callable_function_raises():
    def my_default():
        return 42

    with pytest.raises(ConfigurationError, match="db_default must be a static value"):
        fields.IntField(db_default=my_default)


# ============================================================================
# db_default + default coexistence
# ============================================================================


def test_db_default_and_default_coexist():
    f = fields.IntField(default=1, db_default=2)
    assert f.default == 1
    assert f.db_default == 2
    assert f.has_db_default() is True


# ============================================================================
# describe() tests
# ============================================================================


def test_describe_without_db_default():
    f = fields.IntField()
    f.model_field_name = "test_field"
    desc = f.describe(serializable=True)
    assert "db_default" in desc
    assert desc["db_default"] == "__NOT_SET__"


def test_describe_with_db_default_int():
    f = fields.IntField(db_default=42)
    f.model_field_name = "test_field"
    desc = f.describe(serializable=True)
    assert desc["db_default"] == 42


def test_describe_with_db_default_str():
    f = fields.CharField(max_length=100, db_default="hello")
    f.model_field_name = "test_field"
    desc = f.describe(serializable=True)
    assert desc["db_default"] == "hello"


def test_describe_with_db_default_none():
    f = fields.IntField(null=True, db_default=None)
    f.model_field_name = "test_field"
    desc = f.describe(serializable=True)
    assert desc["db_default"] is None
    # When has_db_default is True and value is None, serializable uses default_name(None) -> None
    assert f.has_db_default() is True


def test_describe_with_db_default_bool():
    f = fields.BooleanField(db_default=True)
    f.model_field_name = "test_field"
    desc = f.describe(serializable=True)
    assert desc["db_default"] is True


def test_describe_non_serializable_with_db_default():
    f = fields.IntField(db_default=42)
    f.model_field_name = "test_field"
    desc = f.describe(serializable=False)
    assert desc["db_default"] == 42


def test_describe_non_serializable_without_db_default():
    f = fields.IntField()
    f.model_field_name = "test_field"
    desc = f.describe(serializable=False)
    assert desc["db_default"] is DB_DEFAULT_NOT_SET


# ============================================================================
# deconstruct() tests
# ============================================================================


def test_deconstruct_without_db_default():
    f = fields.IntField()
    f.model_field_name = "test_field"
    path, args, kwargs = f.deconstruct()
    assert "db_default" not in kwargs


def test_deconstruct_with_db_default_int():
    f = fields.IntField(db_default=42)
    f.model_field_name = "test_field"
    path, args, kwargs = f.deconstruct()
    assert "db_default" in kwargs
    assert kwargs["db_default"] == 42


def test_deconstruct_with_db_default_str():
    f = fields.CharField(max_length=100, db_default="hello")
    f.model_field_name = "test_field"
    path, args, kwargs = f.deconstruct()
    assert kwargs["db_default"] == "hello"


def test_deconstruct_with_db_default_none():
    f = fields.IntField(null=True, db_default=None)
    f.model_field_name = "test_field"
    path, args, kwargs = f.deconstruct()
    assert "db_default" in kwargs
    assert kwargs["db_default"] is None


def test_deconstruct_with_db_default_zero():
    f = fields.IntField(db_default=0)
    f.model_field_name = "test_field"
    path, args, kwargs = f.deconstruct()
    assert "db_default" in kwargs
    assert kwargs["db_default"] == 0


def test_deconstruct_with_db_default_false():
    f = fields.BooleanField(db_default=False)
    f.model_field_name = "test_field"
    path, args, kwargs = f.deconstruct()
    assert "db_default" in kwargs
    assert kwargs["db_default"] is False


def test_deconstruct_with_both_default_and_db_default():
    f = fields.IntField(default=1, db_default=2)
    f.model_field_name = "test_field"
    path, args, kwargs = f.deconstruct()
    assert kwargs["default"] == 1
    assert kwargs["db_default"] == 2


# ============================================================================
# Sentinel behavior
# ============================================================================


def test_sentinel_repr():
    assert repr(DB_DEFAULT_NOT_SET) == "NOT_PROVIDED"


def test_sentinel_bool():
    assert bool(DB_DEFAULT_NOT_SET) is False


def test_sentinel_is_singleton():
    """Verify the sentinel instance is the module-level singleton."""
    f = fields.IntField()
    assert f.db_default is DB_DEFAULT_NOT_SET


# ============================================================================
# __copy__ preserves db_default
# ============================================================================


def test_copy_preserves_db_default():
    import copy

    f = fields.IntField(db_default=42)
    f.model_field_name = "test_field"
    f2 = copy.copy(f)
    assert f2.has_db_default() is True
    assert f2.db_default == 42


def test_copy_preserves_no_db_default():
    import copy

    f = fields.IntField()
    f.model_field_name = "test_field"
    f2 = copy.copy(f)
    assert f2.has_db_default() is False


# ============================================================================
# Schema generation tests (using SQLite generator)
# ============================================================================


def _get_sqlite_default_sql(field_obj, model_class=None):
    """Helper to get the DEFAULT SQL for a field using the SQLite schema generator."""
    from unittest.mock import MagicMock

    from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator

    mock_client = MagicMock()
    mock_client.capabilities.dialect = "sqlite"
    gen = SqliteSchemaGenerator(mock_client)

    if model_class is None:
        model_class = MagicMock()

    return gen._get_field_default(field_obj, "test_table", "test_col", model_class)


def test_schema_db_default_int():
    f = fields.IntField(db_default=42)
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "42" in sql


def test_schema_db_default_str():
    f = fields.CharField(max_length=100, db_default="hello")
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "hello" in sql


def test_schema_db_default_bool_true():
    f = fields.BooleanField(db_default=True)
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "1" in sql


def test_schema_db_default_bool_false():
    f = fields.BooleanField(db_default=False)
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "0" in sql


def test_schema_db_default_none():
    f = fields.IntField(null=True, db_default=None)
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "NULL" in sql


def test_schema_db_default_overrides_default():
    """When both default and db_default are set, db_default controls the SQL."""
    f = fields.IntField(default=1, db_default=2)
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "2" in sql
    assert "1" not in sql


def test_schema_no_db_default_no_default():
    f = fields.IntField()
    sql = _get_sqlite_default_sql(f)
    assert sql == ""


def test_schema_db_default_float():
    f = fields.FloatField(db_default=3.14)
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "3.14" in sql


# ============================================================================
# Migration field signature tests
# ============================================================================


def test_field_signature_includes_db_default():
    """Changing db_default produces different field signatures."""
    from tortoise.migrations.schema_generator.state_diff import _field_signature

    f1 = fields.IntField(db_default=1)
    f1.model_field_name = "val"
    f2 = fields.IntField(db_default=2)
    f2.model_field_name = "val"
    f_none = fields.IntField()
    f_none.model_field_name = "val"

    sig1 = _field_signature(f1)
    sig2 = _field_signature(f2)
    sig_none = _field_signature(f_none)

    assert sig1 != sig2, "Different db_default values should produce different signatures"
    assert sig1 != sig_none, "db_default=1 should differ from no db_default"
    assert sig2 != sig_none, "db_default=2 should differ from no db_default"


def test_field_signature_distinguishes_db_default_none_from_not_set():
    """db_default=None and no db_default should produce different signatures."""
    from tortoise.migrations.schema_generator.state_diff import _field_signature

    f_with_none = fields.IntField(null=True, db_default=None)
    f_with_none.model_field_name = "val"
    f_without = fields.IntField(null=True)
    f_without.model_field_name = "val"

    sig_with_none = _field_signature(f_with_none)
    sig_without = _field_signature(f_without)

    assert sig_with_none != sig_without, (
        "db_default=None should differ from no db_default in field signature"
    )


def test_field_signature_excludes_default():
    """Changing Python-level default should NOT change the field signature."""
    from tortoise.migrations.schema_generator.state_diff import _field_signature

    f1 = fields.IntField(default=1)
    f1.model_field_name = "val"
    f2 = fields.IntField(default=2)
    f2.model_field_name = "val"

    sig1 = _field_signature(f1)
    sig2 = _field_signature(f2)

    assert sig1 == sig2, "Different default values should NOT produce different signatures"


# ============================================================================
# Migration schema editor ALTER / ADD COLUMN tests
# ============================================================================


def _make_model(model_name, table, **model_fields):
    """Create a model class dynamically for migration tests."""
    from tortoise.models import Model

    attrs = dict(model_fields)
    meta = type("Meta", (), {"app": "models", "table": table})
    attrs["Meta"] = meta
    return type(model_name, (Model,), attrs)


def _make_test_editor():
    """Create a BaseSchemaEditor subclass with a FakeClient for testing."""
    from tests.utils.fake_client import FakeClient
    from tortoise.migrations.schema_editor.base import BaseSchemaEditor

    class TestSchemaEditor(BaseSchemaEditor):
        def _get_table_comment_sql(self, table, comment):
            return ""

        def _get_column_comment_sql(self, table, column, comment):
            return ""

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    return editor, client


@pytest.mark.asyncio
async def test_alter_field_sql_set_default():
    """ALTER TABLE generates SET DEFAULT when adding db_default."""
    OldModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(),
    )
    NewModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=10),
    )

    editor, client = _make_test_editor()
    await editor.alter_field(OldModel, NewModel, "score")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "SET DEFAULT" in sql
    assert "10" in sql


@pytest.mark.asyncio
async def test_alter_field_sql_drop_default():
    """ALTER TABLE generates DROP DEFAULT when removing db_default."""
    OldModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=10),
    )
    NewModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(),
    )

    editor, client = _make_test_editor()
    await editor.alter_field(OldModel, NewModel, "score")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "DROP DEFAULT" in sql


@pytest.mark.asyncio
async def test_alter_field_sql_change_default():
    """ALTER TABLE generates SET DEFAULT with the new value when changing db_default."""
    OldModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=10),
    )
    NewModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=20),
    )

    editor, client = _make_test_editor()
    await editor.alter_field(OldModel, NewModel, "score")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "SET DEFAULT" in sql
    assert "20" in sql


@pytest.mark.asyncio
async def test_add_field_with_db_default():
    """ADD COLUMN includes DEFAULT clause when field has db_default."""
    WidgetModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=42),
    )

    editor, client = _make_test_editor()
    await editor.add_field(WidgetModel, "score")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "ADD COLUMN" in sql
    assert "DEFAULT" in sql
    assert "42" in sql


@pytest.mark.asyncio
async def test_add_field_without_db_default_no_default_clause():
    """ADD COLUMN omits DEFAULT clause when field has no db_default."""
    WidgetModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        name=fields.TextField(),
    )

    editor, client = _make_test_editor()
    await editor.add_field(WidgetModel, "name")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "ADD COLUMN" in sql
    assert "DEFAULT" not in sql


# ============================================================================
# SqlDefault and Now expression tests
# ============================================================================


def test_sql_default_construction_and_get_sql():
    """SqlDefault construction and get_sql."""
    from tortoise.fields.db_defaults import SqlDefault

    sd = SqlDefault("CURRENT_TIMESTAMP")
    assert sd.get_sql() == "CURRENT_TIMESTAMP"
    assert sd.get_sql("some_context") == "CURRENT_TIMESTAMP"


def test_now_construction():
    """Now construction."""
    from tortoise.fields.db_defaults import Now

    n = Now()
    assert n.get_sql() == "CURRENT_TIMESTAMP"


def test_now_dialect_mysql():
    """Now emits CURRENT_TIMESTAMP(6) for MySQL."""
    from tortoise.fields.db_defaults import Now

    n = Now()
    assert n.get_sql(dialect="mysql") == "CURRENT_TIMESTAMP(6)"


def test_now_dialect_other():
    """Now emits plain CURRENT_TIMESTAMP for non-MySQL dialects."""
    from tortoise.fields.db_defaults import Now

    n = Now()
    for dialect in ("sqlite", "postgres", "mssql", "oracle", "sql"):
        assert n.get_sql(dialect=dialect) == "CURRENT_TIMESTAMP"


def test_sql_default_equality_and_hashing():
    """SqlDefault equality and hashing."""
    from tortoise.fields.db_defaults import SqlDefault

    a = SqlDefault("X")
    b = SqlDefault("X")
    c = SqlDefault("Y")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)
    # Can be used in sets/dicts
    s = {a, b, c}
    assert len(s) == 2


def test_sql_default_repr():
    """SqlDefault repr."""
    from tortoise.fields.db_defaults import SqlDefault

    assert repr(SqlDefault("CURRENT_TIMESTAMP")) == "SqlDefault('CURRENT_TIMESTAMP')"


def test_now_repr():
    """Now repr."""
    from tortoise.fields.db_defaults import Now

    assert repr(Now()) == "Now()"


def test_sql_default_passes_field_validation():
    """SqlDefault is not callable -- passes field validation."""
    from tortoise.fields.db_defaults import SqlDefault

    # Should not raise
    f = fields.DatetimeField(db_default=SqlDefault("CURRENT_TIMESTAMP"))
    assert f.has_db_default() is True


def test_callable_still_raises_with_updated_message():
    """Callable still raises with SqlDefault in message."""
    with pytest.raises(ConfigurationError, match="SqlDefault"):
        fields.IntField(db_default=lambda: 1)


# ============================================================================
# Schema generation with SqlDefault / Now
# ============================================================================


def test_schema_generation_with_sql_default():
    """Schema generation with SqlDefault."""
    from tortoise.fields.db_defaults import SqlDefault

    f = fields.DatetimeField(db_default=SqlDefault("CURRENT_TIMESTAMP"))
    sql = _get_sqlite_default_sql(f)
    assert sql == " DEFAULT CURRENT_TIMESTAMP"


def test_schema_generation_with_now():
    """Schema generation with Now()."""
    from tortoise.fields.db_defaults import Now

    f = fields.DatetimeField(db_default=Now())
    sql = _get_sqlite_default_sql(f)
    assert sql == " DEFAULT CURRENT_TIMESTAMP"


def test_schema_generation_with_custom_sql_expression():
    """Schema generation with custom SQL expression."""
    from tortoise.fields.db_defaults import SqlDefault

    f = fields.CharField(max_length=100, db_default=SqlDefault("'unknown'"))
    sql = _get_sqlite_default_sql(f)
    assert sql == " DEFAULT 'unknown'"


def test_schema_generation_literal_db_default_still_works():
    """Literal db_default still works (no regression)."""
    f = fields.IntField(db_default=42)
    sql = _get_sqlite_default_sql(f)
    assert "DEFAULT" in sql
    assert "42" in sql


# ============================================================================
# Migration editor with SqlDefault / Now
# ============================================================================


@pytest.mark.asyncio
async def test_add_field_with_sql_default():
    """Migration add_field with SqlDefault."""
    from tortoise.fields.db_defaults import Now

    WidgetModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        created=fields.DatetimeField(db_default=Now()),
    )

    editor, client = _make_test_editor()
    await editor.add_field(WidgetModel, "created")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "DEFAULT CURRENT_TIMESTAMP" in sql


@pytest.mark.asyncio
async def test_alter_field_set_default_with_sql_default():
    """Migration alter_field SET DEFAULT with SqlDefault."""
    from tortoise.fields.db_defaults import Now

    OldModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        created=fields.DatetimeField(),
    )
    NewModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        created=fields.DatetimeField(db_default=Now()),
    )

    editor, client = _make_test_editor()
    await editor.alter_field(OldModel, NewModel, "created")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "SET DEFAULT" in sql
    assert "CURRENT_TIMESTAMP" in sql


@pytest.mark.asyncio
async def test_alter_field_change_from_literal_to_sql_default():
    """Migration alter_field change from literal to SqlDefault."""
    from tortoise.fields.db_defaults import SqlDefault

    OldModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=42),
    )
    NewModel = _make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=SqlDefault("NOW()")),
    )

    editor, client = _make_test_editor()
    await editor.alter_field(OldModel, NewModel, "score")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "SET DEFAULT" in sql
    assert "NOW()" in sql


# ============================================================================
# describe() and deconstruct() with SqlDefault / Now
# ============================================================================


def test_describe_serializable_with_now():
    """describe(serializable=True) with Now."""
    from tortoise.fields.db_defaults import Now

    f = fields.DatetimeField(db_default=Now())
    f.model_field_name = "created"
    desc = f.describe(serializable=True)
    assert desc["db_default"] == "Now()"


def test_describe_non_serializable_with_now():
    """describe(serializable=False) with Now."""
    from tortoise.fields.db_defaults import Now

    n = Now()
    f = fields.DatetimeField(db_default=n)
    f.model_field_name = "created"
    desc = f.describe(serializable=False)
    assert desc["db_default"] is n


def test_deconstruct_with_now():
    """deconstruct() preserves Now instance."""
    from tortoise.fields.db_defaults import Now

    n = Now()
    f = fields.DatetimeField(db_default=n)
    f.model_field_name = "created"
    path, args, kwargs = f.deconstruct()
    assert kwargs["db_default"] is n


def test_render_value_with_now():
    """render_value() preserves Now() in migration files."""
    from tortoise.fields.db_defaults import Now
    from tortoise.migrations.writer import ImportManager, render_value

    imports = ImportManager()
    n = Now()
    result = render_value(n, imports)
    assert result == "Now()"
    assert "Now" in str(imports)


def test_render_value_with_sql_default():
    """render_value() preserves SqlDefault in migration files."""
    from tortoise.fields.db_defaults import SqlDefault
    from tortoise.migrations.writer import ImportManager, render_value

    imports = ImportManager()
    sd = SqlDefault("gen_random_uuid()")
    result = render_value(sd, imports)
    assert result == "SqlDefault('gen_random_uuid()')"
    assert "SqlDefault" in str(imports)
