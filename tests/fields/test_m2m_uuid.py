import pytest

from tests import testmodels
from tortoise.exceptions import OperationalError


# Parameterize to test both standard and source-field models
@pytest.fixture(
    params=[
        pytest.param(
            (testmodels.UUIDPkModel, testmodels.UUIDM2MRelatedModel),
            id="standard",
        ),
        pytest.param(
            (testmodels.UUIDPkSourceModel, testmodels.UUIDM2MRelatedSourceModel),
            id="sourced",
        ),
    ]
)
def m2m_uuid_models(request):
    """
    Fixture providing UUID model classes for M2M tests.

    Tests both standard UUID models and source-field models with customized DB names.
    """
    return request.param


@pytest.mark.asyncio
async def test_empty(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    await UUIDM2MRelatedModel.create()


@pytest.mark.asyncio
async def test__add(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDM2MRelatedModel.create()
    two = await UUIDPkModel.create()
    await one.models.add(two)
    assert await one.models == [two]
    assert await two.peers == [one]


@pytest.mark.asyncio
async def test__add__nothing(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDPkModel.create()
    await one.peers.add()


@pytest.mark.asyncio
async def test__add__reverse(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDM2MRelatedModel.create()
    two = await UUIDPkModel.create()
    await two.peers.add(one)
    assert await one.models == [two]
    assert await two.peers == [one]


@pytest.mark.asyncio
async def test__add__many(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDPkModel.create()
    two = await UUIDM2MRelatedModel.create()
    await one.peers.add(two)
    await one.peers.add(two)
    await two.models.add(one)
    assert await one.peers == [two]
    assert await two.models == [one]


@pytest.mark.asyncio
async def test__add__two(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDPkModel.create()
    two1 = await UUIDM2MRelatedModel.create()
    two2 = await UUIDM2MRelatedModel.create()
    await one.peers.add(two1, two2)
    assert set(await one.peers) == {two1, two2}
    assert await two1.models == [one]
    assert await two2.models == [one]


@pytest.mark.asyncio
async def test__add__two_two(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one1 = await UUIDPkModel.create()
    one2 = await UUIDPkModel.create()
    two1 = await UUIDM2MRelatedModel.create()
    two2 = await UUIDM2MRelatedModel.create()
    await one1.peers.add(two1, two2)
    await one2.peers.add(two1, two2)
    assert set(await one1.peers) == {two1, two2}
    assert set(await one2.peers) == {two1, two2}
    assert set(await two1.models) == {one1, one2}
    assert set(await two2.models) == {one1, one2}


@pytest.mark.asyncio
async def test__remove(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDPkModel.create()
    two1 = await UUIDM2MRelatedModel.create()
    two2 = await UUIDM2MRelatedModel.create()
    await one.peers.add(two1, two2)
    await one.peers.remove(two1)
    assert await one.peers == [two2]
    assert await two1.models == []
    assert await two2.models == [one]


@pytest.mark.asyncio
async def test__remove__many(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDPkModel.create()
    two1 = await UUIDM2MRelatedModel.create()
    two2 = await UUIDM2MRelatedModel.create()
    two3 = await UUIDM2MRelatedModel.create()
    await one.peers.add(two1, two2, two3)
    await one.peers.remove(two1, two2)
    assert await one.peers == [two3]
    assert await two1.models == []
    assert await two2.models == []
    assert await two3.models == [one]


@pytest.mark.asyncio
async def test__remove__blank(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDPkModel.create()
    with pytest.raises(OperationalError, match=r"remove\(\) called on no instances"):
        await one.peers.remove()


@pytest.mark.asyncio
async def test__clear(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = await UUIDPkModel.create()
    two1 = await UUIDM2MRelatedModel.create()
    two2 = await UUIDM2MRelatedModel.create()
    await one.peers.add(two1, two2)
    await one.peers.clear()
    assert await one.peers == []
    assert await two1.models == []
    assert await two2.models == []


@pytest.mark.asyncio
async def test__uninstantiated_add(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = UUIDPkModel()
    two = await UUIDM2MRelatedModel.create()
    with pytest.raises(OperationalError, match=r"You should first call .save\(\) on"):
        await one.peers.add(two)


@pytest.mark.asyncio
async def test__add_uninstantiated(db, m2m_uuid_models):
    UUIDPkModel, UUIDM2MRelatedModel = m2m_uuid_models
    one = UUIDPkModel()
    two = await UUIDM2MRelatedModel.create()
    with pytest.raises(OperationalError, match=r"You should first call .save\(\) on"):
        await two.models.add(one)
