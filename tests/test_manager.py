import pytest

from tests.testmodels import ManagerModel, ManagerModelExtra


@pytest.mark.asyncio
async def test_manager(db):
    """Test custom manager functionality with active status filtering."""
    m1 = await ManagerModel.create()
    m2 = await ManagerModel.create(status=1)

    assert await ManagerModel.all().active().count() == 1
    assert await ManagerModel.all_objects.count() == 2

    assert await ManagerModel.all().active().get_or_none(pk=m1.pk) is None
    assert await ManagerModel.all_objects.get_or_none(pk=m1.pk) is not None
    assert await ManagerModel.get_or_none(pk=m2.pk) is not None

    await ManagerModelExtra.create(extra="extra")
    assert await ManagerModelExtra.all_objects.count() == 1
    assert await ManagerModelExtra.all().count() == 1
