"""
Integration tests for db_default field behavior during INSERT.

These tests verify that fields with db_default:
1. Get DatabaseDefault sentinel set when no value provided
2. Emit DEFAULT keyword in INSERT SQL
3. Have DB-applied defaults fetched back via RETURNING or SELECT
4. Work correctly when user provides explicit values
5. Work with bulk_create (resolving to literal values)
6. Work with save()/update (skipping DatabaseDefault fields)
7. Work with Meta.fetch_db_defaults = False
"""

import datetime
from decimal import Decimal

import pydantic
import pytest

from tests.testmodels import DefaultModel, NoFetchDefaultModel, SqlDefaultModel
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import OperationalError
from tortoise.fields.base import DatabaseDefault
from tortoise.timezone import UTC


class TestDatabaseDefaultSentinel:
    def test_repr(self):
        f = fields.IntField(db_default=1)
        f.model_field_name = "test_field"
        dd = DatabaseDefault(f)
        assert "DatabaseDefault" in repr(dd)

    def test_bool_is_false(self):
        f = fields.IntField(db_default=1)
        dd = DatabaseDefault(f)
        assert bool(dd) is False

    def test_str(self):
        f = fields.IntField(db_default=1)
        dd = DatabaseDefault(f)
        assert str(dd) == "<DB_DEFAULT>"


class TestFieldRequired:
    def test_required_false_with_db_default(self):
        f = fields.CharField(max_length=50, db_default="")
        assert f.required is False


class TestGetDbDefaultValue:
    def test_returns_database_default_when_has_db_default(self):
        f = fields.IntField(db_default=42)
        result = f.get_db_default_value()
        assert isinstance(result, DatabaseDefault)
        assert result.field is f

    def test_returns_none_when_no_db_default(self):
        f = fields.IntField()
        result = f.get_db_default_value()
        assert result is None


class TestModelInitDbDefault:
    @pytest.mark.asyncio
    async def test_init_sets_database_default(self, db):

        instance = DefaultModel()
        assert isinstance(instance.int_default, DatabaseDefault)
        assert isinstance(instance.char_default, DatabaseDefault)
        assert isinstance(instance.bool_default, DatabaseDefault)
        assert isinstance(instance.float_default, DatabaseDefault)

    @pytest.mark.asyncio
    async def test_init_with_explicit_value(self, db):

        instance = DefaultModel(int_default=42)
        assert instance.int_default == 42
        assert isinstance(instance.char_default, DatabaseDefault)


class TestConstructWithDbDefault:
    @pytest.mark.asyncio
    async def test_construct_sets_database_default(self, db):

        instance = DefaultModel.construct()
        assert isinstance(instance.int_default, DatabaseDefault)
        assert isinstance(instance.char_default, DatabaseDefault)


class TestCreateWithDbDefault:
    @pytest.mark.asyncio
    async def test_create_no_args_applies_db_defaults_and_persists(self, db):

        instance = await DefaultModel.create()
        assert instance.pk is not None
        assert instance.int_default == 1
        assert instance.float_default == 1.5
        assert instance.bool_default is True
        assert instance.char_default == "tortoise"

        refreshed = await DefaultModel.get(pk=instance.pk)
        assert refreshed.int_default == 1
        assert refreshed.char_default == "tortoise"
        assert refreshed.bool_default is True
        assert refreshed.float_default == 1.5

    @pytest.mark.asyncio
    async def test_create_with_partial_override(self, db):

        instance = await DefaultModel.create(int_default=99, char_default="custom")
        assert instance.int_default == 99
        assert instance.char_default == "custom"
        assert instance.bool_default is True

        instance2 = await DefaultModel.create(int_default=42)
        assert instance2.int_default == 42
        assert instance2.char_default == "tortoise"

    @pytest.mark.asyncio
    async def test_create_all_explicit_values(self, db):
        """When all values are provided, cached query path is used (no DEFAULT keyword)."""
        instance = await DefaultModel.create(
            int_default=10,
            float_default=2.5,
            decimal_default=Decimal("3.14"),
            bool_default=False,
            char_default="all_set",
            date_default=datetime.date(2024, 1, 1),
            datetime_default=datetime.datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert instance.int_default == 10
        assert instance.float_default == 2.5
        assert instance.char_default == "all_set"
        assert instance.bool_default is False


class TestBulkCreateWithDbDefault:
    @pytest.mark.asyncio
    async def test_bulk_create_all_defaults(self, db):

        instances = [DefaultModel() for _ in range(3)]
        await DefaultModel.bulk_create(instances)
        all_inst = await DefaultModel.all()
        assert len(all_inst) == 3
        for inst in all_inst:
            assert inst.int_default == 1
            assert inst.char_default == "tortoise"

    @pytest.mark.asyncio
    async def test_bulk_create_all_explicit_values(self, db):
        """When all instances provide explicit values for a db_default field, column is included."""

        inst1 = DefaultModel(int_default=99)
        inst2 = DefaultModel(int_default=77)
        await DefaultModel.bulk_create([inst1, inst2])
        all_inst = await DefaultModel.all().order_by("id")
        assert all_inst[0].int_default == 99
        assert all_inst[1].int_default == 77

    @pytest.mark.asyncio
    async def test_bulk_create_mixed_raises(self, db):
        """Mixed usage (some default, some explicit) for same field raises OperationalError."""
        inst1 = DefaultModel(int_default=99)
        inst2 = DefaultModel()  # int_default is DatabaseDefault
        with pytest.raises(OperationalError, match="Cannot use bulk_create"):
            await DefaultModel.bulk_create([inst1, inst2])

    @pytest.mark.asyncio
    async def test_bulk_create_sql_default_all_defaults_omits_column(self, db):
        """bulk_create with SqlDefault fields where all use default should omit the column."""
        instances = [SqlDefaultModel(name="test1"), SqlDefaultModel(name="test2")]
        await SqlDefaultModel.bulk_create(instances)
        all_inst = await SqlDefaultModel.all()
        assert len(all_inst) == 2
        for inst in all_inst:
            assert inst.created_at is not None
            assert inst.counter == 0

    @pytest.mark.asyncio
    async def test_bulk_create_allowed_with_fetch_false(self, db):
        """bulk_create with db_default fields on fetch_db_defaults=False model should work."""
        instances = [NoFetchDefaultModel() for _ in range(3)]
        await NoFetchDefaultModel.bulk_create(instances)
        all_inst = await NoFetchDefaultModel.all()
        assert len(all_inst) == 3
        for inst in all_inst:
            assert inst.int_val == 1
            assert inst.char_val == "test"


class TestSaveUpdateWithDbDefault:
    @pytest.mark.asyncio
    async def test_update_skips_database_default_fields(self, db):

        instance = await DefaultModel.create()

        # Targeted update with update_fields
        instance.int_default = 42
        await instance.save(update_fields=["int_default"])
        refreshed = await DefaultModel.get(pk=instance.pk)
        assert refreshed.int_default == 42
        assert refreshed.char_default == "tortoise"

        # Full save() should also skip DatabaseDefault fields
        refreshed.int_default = 99
        await refreshed.save()
        final = await DefaultModel.get(pk=instance.pk)
        assert final.int_default == 99
        assert final.char_default == "tortoise"


class TestNoFetchDbDefaults:
    @pytest.mark.asyncio
    async def test_create_with_no_fetch(self, db):
        """Models with fetch_db_defaults=False still emit DEFAULT keyword.

        On RETURNING backends (sqlite, pg), values are populated via RETURNING
        regardless of fetch_db_defaults.
        On non-RETURNING backends (mysql), values remain DatabaseDefault on the
        in-memory instance since the post-INSERT SELECT is skipped.
        """
        conn = db.db()

        instance = await NoFetchDefaultModel.create()
        assert instance.pk is not None

        if conn.capabilities.support_returning:
            # RETURNING populates values regardless of fetch_db_defaults
            assert instance.int_val == 1
            assert instance.char_val == "test"
        else:
            # Non-RETURNING backends skip the post-INSERT SELECT
            assert isinstance(instance.int_val, DatabaseDefault)
            assert isinstance(instance.char_val, DatabaseDefault)

        # A fresh SELECT always returns the real values
        refreshed = await NoFetchDefaultModel.get(pk=instance.pk)
        assert refreshed.int_val == 1
        assert refreshed.char_val == "test"


class TestMetaInfo:
    @pytest.mark.asyncio
    async def test_db_default_meta_attributes(self, db):
        meta = DefaultModel._meta
        assert len(meta.db_default_db_columns) > 0
        assert "int_default" in meta.db_default_db_columns
        assert "char_default" in meta.db_default_db_columns
        assert meta.fetch_db_defaults is True

        assert NoFetchDefaultModel._meta.fetch_db_defaults is False


class TestPydanticDbDefault:
    @pytest.mark.asyncio
    async def test_pydantic_no_fetch_requires_refresh(self, db):
        PydanticNoFetch = pydantic_model_creator(NoFetchDefaultModel)

        instance = await NoFetchDefaultModel.create()
        conn = instance._meta.db

        if not conn.capabilities.support_returning:
            # Without RETURNING, unfetched db_default fields are DatabaseDefault sentinels
            # and pydantic validation will fail
            with pytest.raises(pydantic.ValidationError):
                await PydanticNoFetch.from_tortoise_orm(instance)

        # After refreshing from db, pydantic model succeeds
        refreshed = await NoFetchDefaultModel.get(pk=instance.pk)
        pydantic_instance = await PydanticNoFetch.from_tortoise_orm(refreshed)
        assert pydantic_instance.int_val == 1
        assert pydantic_instance.char_val == "test"
