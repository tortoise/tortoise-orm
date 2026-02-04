import pytest

from tests.testmodels import OldStyleModel, Tournament


@pytest.mark.asyncio
async def test_basic(db):
    """Test basic CRUD operations with Tournament model."""
    tournament = await Tournament.create(name="Test")
    await Tournament.filter(id=tournament.id).update(name="Updated name")
    saved_event = await Tournament.filter(name="Updated name").first()
    assert saved_event.id == tournament.id

    await Tournament(name="Test 2").save()
    assert await Tournament.all().values_list("id", flat=True) == [
        tournament.id,
        tournament.id + 1,
    ]

    # Compare sorted by id to ensure consistent ordering
    result = await Tournament.all().values("id", "name")
    expected = [
        {"id": tournament.id, "name": "Updated name"},
        {"id": tournament.id + 1, "name": "Test 2"},
    ]
    assert sorted(result, key=lambda x: x["id"]) == sorted(expected, key=lambda x: x["id"])


@pytest.mark.asyncio
async def test_basic_oldstyle(db):
    """Test OldStyleModel with external_id field."""
    obj = await OldStyleModel.create(external_id=123)
    assert obj.pk

    assert OldStyleModel._meta.fields_map["id"].pk
    assert OldStyleModel._meta.fields_map["external_id"].index
