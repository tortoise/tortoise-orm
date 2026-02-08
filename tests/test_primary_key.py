from __future__ import annotations

import uuid
from typing import Any

import pytest

from tests.testmodels import (
    CharFkRelatedModel,
    CharM2MRelatedModel,
    CharPkModel,
    ImplicitPkModel,
    UUIDFkRelatedModel,
    UUIDM2MRelatedModel,
    UUIDPkModel,
)
from tortoise import fields
from tortoise.exceptions import ConfigurationError


class TestQueryset:
    @pytest.mark.asyncio
    async def test_implicit_pk(self, db):
        instance = await ImplicitPkModel.create(value="test")
        assert instance.id
        assert instance.pk == instance.id

    @pytest.mark.asyncio
    async def test_uuid_pk(self, db):
        value = uuid.uuid4()
        await UUIDPkModel.create(id=value)

        instance2 = await UUIDPkModel.get(id=value)
        assert instance2.id == value
        assert instance2.pk == value

    @pytest.mark.asyncio
    async def test_uuid_pk_default(self, db):
        instance1 = await UUIDPkModel.create()
        assert isinstance(instance1.id, uuid.UUID)
        assert instance1.pk == instance1.pk

        instance2 = await UUIDPkModel.get(id=instance1.id)
        assert instance2.id == instance1.id
        assert instance2.pk == instance1.id

    @pytest.mark.asyncio
    async def test_uuid_pk_fk(self, db):
        value = uuid.uuid4()
        instance = await UUIDPkModel.create(id=value)
        instance2 = await UUIDPkModel.create(id=uuid.uuid4())
        await UUIDFkRelatedModel.create(model=instance2)

        related_instance = await UUIDFkRelatedModel.create(model=instance)
        assert related_instance.model_id == value

        related_instance = await UUIDFkRelatedModel.filter(model=instance).first()
        assert related_instance.model_id == value

        related_instance = await UUIDFkRelatedModel.filter(model_id=value).first()
        assert related_instance.model_id == value

        await related_instance.fetch_related("model")
        assert related_instance.model == instance

        await instance.fetch_related("children")
        assert instance.children[0] == related_instance

    @pytest.mark.asyncio
    async def test_uuid_m2m(self, db):
        value = uuid.uuid4()
        instance = await UUIDPkModel.create(id=value)
        instance2 = await UUIDPkModel.create(id=uuid.uuid4())

        related_instance = await UUIDM2MRelatedModel.create()
        related_instance2 = await UUIDM2MRelatedModel.create()

        await instance.peers.add(related_instance)
        await related_instance2.models.add(instance, instance2)

        await instance.fetch_related("peers")
        assert len(instance.peers) == 2
        assert set(instance.peers) == {related_instance, related_instance2}

        await related_instance.fetch_related("models")
        assert len(related_instance.models) == 1
        assert related_instance.models[0] == instance

        await related_instance2.fetch_related("models")
        assert len(related_instance2.models) == 2
        assert {m.pk for m in related_instance2.models} == {instance.pk, instance2.pk}

        related_instance_list = await UUIDM2MRelatedModel.filter(models=instance2)
        assert len(related_instance_list) == 1
        assert related_instance_list[0] == related_instance2

        related_instance_list = await UUIDM2MRelatedModel.filter(models__in=[instance2])
        assert len(related_instance_list) == 1
        assert related_instance_list[0] == related_instance2

    @pytest.mark.asyncio
    async def test_char_pk(self, db):
        value = "Da-PK"
        await CharPkModel.create(id=value)

        instance2 = await CharPkModel.get(id=value)
        assert instance2.id == value
        assert instance2.pk == value

    @pytest.mark.asyncio
    async def test_char_pk_fk(self, db):
        value = "Da-PK-for-FK"
        instance = await CharPkModel.create(id=value)
        instance2 = await CharPkModel.create(id=uuid.uuid4())
        await CharFkRelatedModel.create(model=instance2)

        related_instance = await CharFkRelatedModel.create(model=instance)
        assert related_instance.model_id == value

        related_instance = await CharFkRelatedModel.filter(model=instance).first()
        assert related_instance.model_id == value

        related_instance = await CharFkRelatedModel.filter(model_id=value).first()
        assert related_instance.model_id == value

        await instance.fetch_related("children")
        assert instance.children[0] == related_instance

    @pytest.mark.asyncio
    async def test_char_m2m(self, db):
        value = "Da-PK-for-M2M"
        instance = await CharPkModel.create(id=value)
        instance2 = await CharPkModel.create(id=uuid.uuid4())

        related_instance = await CharM2MRelatedModel.create()
        related_instance2 = await CharM2MRelatedModel.create()

        await instance.peers.add(related_instance)
        await related_instance2.models.add(instance, instance2)

        await related_instance.fetch_related("models")
        assert len(related_instance.models) == 1
        assert related_instance.models[0] == instance

        await related_instance2.fetch_related("models")
        assert len(related_instance2.models) == 2
        assert {m.pk for m in related_instance2.models} == {instance.pk, instance2.pk}

        related_instance_list = await CharM2MRelatedModel.filter(models=instance2)
        assert len(related_instance_list) == 1
        assert related_instance_list[0] == related_instance2

        related_instance_list = await CharM2MRelatedModel.filter(models__in=[instance2])
        assert len(related_instance_list) == 1
        assert related_instance_list[0] == related_instance2


# Test parameters for pk index alias tests
# Format: (Field class, init_kwargs, field_id)
PK_INDEX_ALIAS_PARAMS = [
    pytest.param(fields.CharField, {"max_length": 10}, id="CharField"),
    pytest.param(fields.UUIDField, {}, id="UUIDField"),
    pytest.param(fields.IntField, {}, id="IntField"),
    pytest.param(fields.BigIntField, {}, id="BigIntField"),
    pytest.param(fields.SmallIntField, {}, id="SmallIntField"),
]


class TestPkIndexAlias:
    """Test pk alias functionality for various field types."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("Field,init_kwargs", PK_INDEX_ALIAS_PARAMS)
    async def test_pk_alias_warning(self, Field: Any, init_kwargs: dict):
        msg = "`pk` is deprecated, please use `primary_key` instead"
        with pytest.warns(DeprecationWarning, match=msg):
            f = Field(pk=True, **init_kwargs)
        assert f.pk is True
        with pytest.warns(DeprecationWarning, match=msg):
            f = Field(pk=False, **init_kwargs)
        assert f.pk is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("Field,init_kwargs", PK_INDEX_ALIAS_PARAMS)
    async def test_pk_alias_error(self, Field: Any, init_kwargs: dict):
        with pytest.raises(ConfigurationError):
            Field(pk=True, primary_key=False, **init_kwargs)
        with pytest.raises(ConfigurationError):
            Field(pk=False, primary_key=True, **init_kwargs)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("Field,init_kwargs", PK_INDEX_ALIAS_PARAMS)
    async def test_pk_alias_compare(self, Field: Any, init_kwargs: dict):
        # Only for compare, not recommended
        f = Field(pk=True, primary_key=True, **init_kwargs)
        assert f.pk is True
        f = Field(pk=False, primary_key=False, **init_kwargs)
        assert f.pk is False


class TestPkIndexAliasUUID:
    """UUID-specific pk alias tests."""

    @pytest.mark.asyncio
    async def test_default(self):
        msg = "`pk` is deprecated, please use `primary_key` instead"
        with pytest.warns(DeprecationWarning, match=msg):
            f = fields.UUIDField(pk=True)
        assert f.default == uuid.uuid4
        f = fields.UUIDField(primary_key=True)
        assert f.default == uuid.uuid4
        f = fields.UUIDField()
        assert f.default is None
        f = fields.UUIDField(default=1)
        assert f.default == 1


# Int field types that support positional pk argument
INT_FIELD_TYPES = [
    pytest.param(fields.IntField, id="IntField"),
    pytest.param(fields.BigIntField, id="BigIntField"),
    pytest.param(fields.SmallIntField, id="SmallIntField"),
]


class TestPkIndexAliasInt:
    """Int field types support positional pk argument."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("Field", INT_FIELD_TYPES)
    async def test_argument(self, Field: Any):
        f = Field(True)
        assert f.pk is True
        f = Field(False)
        assert f.pk is False


class TestPkIndexAliasText:
    """TextField pk alias tests with deprecation warnings."""

    message = "TextField as a PrimaryKey is Deprecated, use CharField instead"
    pk_deprecation_msg = "`pk` is deprecated, please use `primary_key` instead"

    def test_warning(self):
        # TextField(pk=True) emits both warnings: pk deprecation and TextField as PK
        with pytest.warns(DeprecationWarning, match=self.message):
            f = fields.TextField(pk=True)
        assert f.pk is True
        with pytest.warns(DeprecationWarning, match=self.message):
            f = fields.TextField(primary_key=True)
        assert f.pk is True
        # Positional arg goes to primary_key, so only TextField as PK warning
        with pytest.warns(DeprecationWarning, match=self.message):
            f = fields.TextField(True)
        assert f.pk is True

    @pytest.mark.asyncio
    async def test_pk_alias_warning(self):
        # TextField(pk=True) emits TextField as PK warning (and pk deprecation)
        with pytest.warns(DeprecationWarning, match=self.message):
            f = fields.TextField(pk=True)
        assert f.pk is True
        # pk=False does not trigger TextField as PK warning, but triggers pk deprecation
        with pytest.warns(DeprecationWarning, match=self.pk_deprecation_msg):
            f = fields.TextField(pk=False)
        assert f.pk is False

    @pytest.mark.asyncio
    async def test_pk_alias_error(self):
        # Both pk=True and primary_key=False triggers TextField warning first, then raises
        with pytest.raises(ConfigurationError):
            with pytest.warns(DeprecationWarning, match=self.message):
                fields.TextField(pk=True, primary_key=False)
        # pk=False and primary_key=True triggers TextField as PK warning, then raises
        with pytest.raises(ConfigurationError):
            with pytest.warns(DeprecationWarning, match=self.message):
                fields.TextField(pk=False, primary_key=True)

    @pytest.mark.asyncio
    async def test_pk_alias_compare(self):
        # Both pk=True and primary_key=True: TextField as PK warning is emitted
        with pytest.warns(DeprecationWarning, match=self.message):
            f = fields.TextField(pk=True, primary_key=True)
        assert f.pk is True
        # pk=False and primary_key=False: no warnings
        f = fields.TextField(pk=False, primary_key=False)
        assert f.pk is False
