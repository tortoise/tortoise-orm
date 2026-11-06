import uuid

import pytest

from tests import testmodels
from tortoise import fields
from tortoise.exceptions import IntegrityError, ValidationError


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.UUIDFields.create()


@pytest.mark.asyncio
async def test_create(db):
    data = uuid.uuid4()
    obj0 = await testmodels.UUIDFields.create(data=data)
    assert isinstance(obj0.data, uuid.UUID)
    assert isinstance(obj0.data_auto, uuid.UUID)
    assert obj0.data_null is None
    obj = await testmodels.UUIDFields.get(id=obj0.id)
    assert isinstance(obj.data, uuid.UUID)
    assert isinstance(obj.data_auto, uuid.UUID)
    assert obj.data == data
    assert obj.data_null is None
    await obj.save()
    obj2 = await testmodels.UUIDFields.get(id=obj.id)
    assert obj == obj2

    await obj.delete()
    obj = await testmodels.UUIDFields.filter(id=obj0.id).first()
    assert obj is None


@pytest.mark.asyncio
async def test_update(db):
    data = uuid.uuid4()
    data2 = uuid.uuid4()
    obj0 = await testmodels.UUIDFields.create(data=data)
    await testmodels.UUIDFields.filter(id=obj0.id).update(data=data2)
    obj = await testmodels.UUIDFields.get(id=obj0.id)
    assert obj.data == data2
    assert obj.data_null is None


@pytest.mark.asyncio
async def test_create_not_null(db):
    data = uuid.uuid4()
    obj0 = await testmodels.UUIDFields.create(data=data, data_null=data)
    obj = await testmodels.UUIDFields.get(id=obj0.id)
    assert obj.data == data
    assert obj.data_null == data


@pytest.mark.parametrize("as_string", [False, True])
def test_uuid_field_validators(as_string):
    def validate_version(value):
        if value.version != 4:
            raise ValidationError("UUID must be version 4")

    field = fields.UUIDField(validators=[validate_version])
    valid = uuid.uuid4()
    invalid = uuid.uuid1()
    assert field.to_db_value(str(valid) if as_string else valid, testmodels.UUIDFields) == str(
        valid
    )
    with pytest.raises(ValidationError, match="UUID must be version 4"):
        field.to_db_value(str(invalid) if as_string else invalid, testmodels.UUIDFields)

    nullable = fields.UUIDField(null=True, validators=[validate_version])
    assert nullable.to_db_value(None, testmodels.UUIDFields) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("as_string", [False, True])
async def test_uuid_validator_on_writes(db, monkeypatch, as_string):
    def reject_nil_uuid(value):
        if value.int == 0:
            raise ValidationError("Nil UUID is not allowed")

    field = testmodels.UUIDFields._meta.fields_map["data"]
    monkeypatch.setattr(field, "validators", [reject_nil_uuid])
    nil = uuid.UUID(int=0)
    invalid = str(nil) if as_string else nil
    with pytest.raises(ValidationError, match="Nil UUID is not allowed"):
        await testmodels.UUIDFields.create(data=invalid)

    valid = uuid.uuid4()
    obj = await testmodels.UUIDFields.create(data=str(valid) if as_string else valid)
    with pytest.raises(ValidationError, match="Nil UUID is not allowed"):
        await testmodels.UUIDFields.filter(pk=obj.pk).update(data=invalid)

    replacement = uuid.uuid4()
    await testmodels.UUIDFields.filter(pk=obj.pk).update(
        data=str(replacement) if as_string else replacement
    )
    await obj.refresh_from_db()
    assert obj.data == replacement

    obj.data = invalid
    with pytest.raises(ValidationError, match="Nil UUID is not allowed"):
        await obj.save(update_fields=["data"])
