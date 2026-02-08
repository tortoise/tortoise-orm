import pytest

from tests import testmodels


@pytest.mark.asyncio
async def test_default_create(db):
    model = await testmodels.CallableDefault.create()
    assert model.callable_default == "callable_default"
    assert model.async_default == "async_callable_default"


@pytest.mark.asyncio
async def test_default_by_save(db):
    saved_model = testmodels.CallableDefault()
    await saved_model.save()
    assert saved_model.callable_default == "callable_default"
    assert saved_model.async_default == "async_callable_default"


@pytest.mark.asyncio
async def test_async_default_change(db):
    default_change = testmodels.CallableDefault()
    default_change.async_default = "changed"
    await default_change.save()
    assert default_change.async_default == "changed"
