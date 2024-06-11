from tests.testmodels import OldStyleModel, Tournament
from tortoise.contrib import test


class TestBasic(test.TestCase):
    async def test_basic(self):
        tournament = await Tournament.create(name="Test")
        await Tournament.filter(id=tournament.id).update(name="Updated name")
        saved_event = await Tournament.filter(name="Updated name").first()
        self.assertEqual(saved_event.id, tournament.id)
        await Tournament(name="Test 2").save()
        self.assertEqual(
            await Tournament.all().values_list("id", flat=True),
            [tournament.id, tournament.id + 1],
        )
        self.assertListSortEqual(
            await Tournament.all().values("id", "name"),
            [
                {"id": tournament.id, "name": "Updated name"},
                {"id": tournament.id + 1, "name": "Test 2"},
            ],
            sorted_key="id",
        )

    async def test_basic_oldstyle(self):
        obj = await OldStyleModel.create(external_id=123)
        assert obj.pk

        assert OldStyleModel._meta.fields_map["id"].pk
        assert OldStyleModel._meta.fields_map["external_id"].index
