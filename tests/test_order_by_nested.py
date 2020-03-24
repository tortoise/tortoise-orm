from tests.testmodels import Event, Tournament
from tortoise.contrib import test


class TestOrderByNested(test.TestCase):
    async def test_basic(self):
        await Event.create(
            name="Event 1", tournament=await Tournament.create(name="Tournament 1", desc="B")
        )
        await Event.create(
            name="Event 2", tournament=await Tournament.create(name="Tournament 2", desc="A")
        )

        self.assertEqual(
            await Event.all().order_by("-name").values("name"),
            [{"name": "Event 2"}, {"name": "Event 1"}],
        )

        self.assertEqual(
            await Event.all().prefetch_related("tournament").values("tournament__desc"),
            [{"tournament__desc": "B"}, {"tournament__desc": "A"}],
        )

        self.assertEqual(
            await Event.all()
            .prefetch_related("tournament")
            .order_by("tournament__desc")
            .values("tournament__desc"),
            [{"tournament__desc": "A"}, {"tournament__desc": "B"}],
        )
