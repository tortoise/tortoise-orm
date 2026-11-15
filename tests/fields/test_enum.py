from enum import IntEnum

import pytest

from tests import testmodels
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.fields import CharEnumField, IntEnumField
from tortoise.transactions import in_transaction


class BadIntEnum1(IntEnum):
    python_programming = 32768
    database_design = 2
    system_administration = 3


class BadIntEnum2(IntEnum):
    python_programming = -32769
    database_design = 2
    system_administration = 3


class BadIntEnumIfGenerated(IntEnum):
    python_programming = -1
    database_design = 2
    system_administration = 3


# ============================================================================
# TestIntEnumFields
# ============================================================================


@pytest.mark.asyncio
async def test_int_enum_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.EnumFields.create()


@pytest.mark.asyncio
async def test_int_enum_create(db):
    obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
    assert isinstance(obj0.service, testmodels.Service)
    obj = await testmodels.EnumFields.get(id=obj0.id)
    assert isinstance(obj.service, testmodels.Service)
    assert obj.service == testmodels.Service.system_administration
    await obj.save()
    obj2 = await testmodels.EnumFields.get(id=obj.id)
    assert obj == obj2

    await obj.delete()
    obj = await testmodels.EnumFields.filter(id=obj0.id).first()
    assert obj is None

    obj3 = await testmodels.EnumFields.create(service=3)
    assert isinstance(obj3.service, testmodels.Service)
    with pytest.raises(ValueError):
        await testmodels.EnumFields.create(service=4)


@pytest.mark.asyncio
async def test_int_enum_update(db):
    obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
    await testmodels.EnumFields.filter(id=obj0.id).update(
        service=testmodels.Service.database_design
    )
    obj = await testmodels.EnumFields.get(id=obj0.id)
    assert obj.service == testmodels.Service.database_design

    await testmodels.EnumFields.filter(id=obj0.id).update(service=2)
    obj = await testmodels.EnumFields.get(id=obj0.id)
    assert obj.service == testmodels.Service.database_design
    with pytest.raises(ValueError):
        await testmodels.EnumFields.filter(id=obj0.id).update(service=4)


@pytest.mark.asyncio
async def test_int_enum_values(db):
    obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
    values = await testmodels.EnumFields.get(id=obj0.id).values("service")
    assert values["service"] == testmodels.Service.system_administration

    obj1 = await testmodels.EnumFields.create(service=3)
    values = await testmodels.EnumFields.get(id=obj1.id).values("service")
    assert values["service"] == testmodels.Service.system_administration


@pytest.mark.asyncio
async def test_int_enum_values_list(db):
    obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
    values = await testmodels.EnumFields.get(id=obj0.id).values_list("service", flat=True)
    assert values == testmodels.Service.system_administration

    obj1 = await testmodels.EnumFields.create(service=3)
    values = await testmodels.EnumFields.get(id=obj1.id).values_list("service", flat=True)
    assert values == testmodels.Service.system_administration


def test_int_enum_char_fails():
    with pytest.raises(ConfigurationError, match="IntEnumField only supports integer enums!"):
        IntEnumField(testmodels.Currency)


def test_int_enum_range1_fails():
    with pytest.raises(
        ConfigurationError, match="The valid range of IntEnumField's values is -32768..32767!"
    ):
        IntEnumField(BadIntEnum1)


def test_int_enum_range2_fails():
    with pytest.raises(
        ConfigurationError, match="The valid range of IntEnumField's values is -32768..32767!"
    ):
        IntEnumField(BadIntEnum2)


def test_int_enum_range3_generated_fails():
    with pytest.raises(
        ConfigurationError, match="The valid range of IntEnumField's values is 1..32767!"
    ):
        IntEnumField(BadIntEnumIfGenerated, generated=True)


def test_int_enum_range3_manual():
    fld = IntEnumField(BadIntEnumIfGenerated)
    assert fld.enum_type is BadIntEnumIfGenerated


def test_int_enum_auto_description():
    fld = IntEnumField(testmodels.Service)
    assert fld.description == "python_programming: 1\ndatabase_design: 2\nsystem_administration: 3"


def test_int_enum_manual_description():
    fld = IntEnumField(testmodels.Service, description="foo")
    assert fld.description == "foo"


# ============================================================================
# TestCharEnumFields
# ============================================================================


@pytest.mark.asyncio
async def test_char_enum_create(db):
    obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
    assert isinstance(obj0.currency, testmodels.Currency)
    obj = await testmodels.EnumFields.get(id=obj0.id)
    assert isinstance(obj.currency, testmodels.Currency)
    assert obj.currency == testmodels.Currency.HUF
    await obj.save()
    obj2 = await testmodels.EnumFields.get(id=obj.id)
    assert obj == obj2

    await obj.delete()
    obj = await testmodels.EnumFields.filter(id=obj0.id).first()
    assert obj is None

    obj0 = await testmodels.EnumFields.create(
        service=testmodels.Service.system_administration, currency="USD"
    )
    assert isinstance(obj0.currency, testmodels.Currency)
    with pytest.raises(ValueError):
        await testmodels.EnumFields.create(
            service=testmodels.Service.system_administration, currency="XXX"
        )


@pytest.mark.asyncio
async def test_char_enum_update(db):
    obj0 = await testmodels.EnumFields.create(
        service=testmodels.Service.system_administration, currency=testmodels.Currency.HUF
    )
    await testmodels.EnumFields.filter(id=obj0.id).update(currency=testmodels.Currency.EUR)
    obj = await testmodels.EnumFields.get(id=obj0.id)
    assert obj.currency == testmodels.Currency.EUR

    await testmodels.EnumFields.filter(id=obj0.id).update(currency="USD")
    obj = await testmodels.EnumFields.get(id=obj0.id)
    assert obj.currency == testmodels.Currency.USD
    with pytest.raises(ValueError):
        await testmodels.EnumFields.filter(id=obj0.id).update(currency="XXX")


@pytest.mark.asyncio
async def test_char_enum_values(db):
    obj0 = await testmodels.EnumFields.create(
        service=testmodels.Service.system_administration, currency=testmodels.Currency.EUR
    )
    values = await testmodels.EnumFields.get(id=obj0.id).values("currency")
    assert values["currency"] == testmodels.Currency.EUR

    obj1 = await testmodels.EnumFields.create(service=3, currency="EUR")
    values = await testmodels.EnumFields.get(id=obj1.id).values("currency")
    assert values["currency"] == testmodels.Currency.EUR


@pytest.mark.asyncio
async def test_char_enum_values_list(db):
    obj0 = await testmodels.EnumFields.create(
        service=testmodels.Service.system_administration, currency=testmodels.Currency.EUR
    )
    values = await testmodels.EnumFields.get(id=obj0.id).values_list("currency", flat=True)
    assert values == testmodels.Currency.EUR

    obj1 = await testmodels.EnumFields.create(service=3, currency="EUR")
    values = await testmodels.EnumFields.get(id=obj1.id).values_list("currency", flat=True)
    assert values == testmodels.Currency.EUR


def test_char_enum_auto_maxlen():
    fld = CharEnumField(testmodels.Currency)
    assert fld.max_length == 3


def test_char_enum_defined_maxlen():
    fld = CharEnumField(testmodels.Currency, max_length=5)
    assert fld.max_length == 5


def test_char_enum_auto_description():
    fld = CharEnumField(testmodels.Currency)
    assert fld.description == "HUF: HUF\nEUR: EUR\nUSD: USD"


def test_char_enum_manual_description():
    fld = CharEnumField(testmodels.Currency, description="baa")
    assert fld.description == "baa"


@pytest.mark.parametrize("primary_key", [False, True])
@pytest.mark.parametrize("generated", [False, True])
def test_int_enum_generated_flag(primary_key, generated):
    fld = IntEnumField(testmodels.Service, primary_key=primary_key, generated=generated)
    assert fld.generated is generated
    assert fld.describe(serializable=False)["generated"] is generated
    _, args, kwargs = fld.deconstruct()
    assert type(fld)(*args, **kwargs).generated is generated


def test_int_enum_generated_defaults():
    assert IntEnumField(testmodels.Service).generated is False
    assert IntEnumField(testmodels.Service, primary_key=True).generated is True
    assert IntEnumField(testmodels.Service, pk=True).generated is True


@pytest.mark.asyncio
async def test_int_enum_manual_primary_key(db):
    with pytest.raises(IntegrityError):
        async with in_transaction():
            await testmodels.EnumManualPk.create()
    obj = await testmodels.EnumManualPk.create(id=testmodels.Service.database_design)
    assert (await testmodels.EnumManualPk.get(pk=obj.pk)).pk is testmodels.Service.database_design
