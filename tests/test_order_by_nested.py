import pytest

from tests.testmodels import Event, Tournament
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ


@test.requireCapability(dialect=NotEQ("oracle"))
@pytest.mark.asyncio
async def test_order_by_nested_basic(db):
    await Event.create(
        name="Event 1", tournament=await Tournament.create(name="Tournament 1", desc="B")
    )
    await Event.create(
        name="Event 2", tournament=await Tournament.create(name="Tournament 2", desc="A")
    )

    assert await Event.all().order_by("-name").values("name") == [
        {"name": "Event 2"},
        {"name": "Event 1"},
    ]

    assert await Event.all().prefetch_related("tournament").values("tournament__desc") == [
        {"tournament__desc": "B"},
        {"tournament__desc": "A"},
    ]

    assert (
        await Event.all()
        .prefetch_related("tournament")
        .order_by("tournament__desc")
        .values("tournament__desc")
    ) == [{"tournament__desc": "A"}, {"tournament__desc": "B"}]
