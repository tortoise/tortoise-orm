from datetime import datetime, timedelta
from typing import Any

from pypika.terms import Function

from tests.testmodels import DefaultUpdate, Event, IntFields, JSONFields, Tournament
from tortoise.contrib import test
from tortoise.expressions import F


class TestUpdate(test.TestCase):
    async def test_update(self):
        await Tournament.create(name="1")
        await Tournament.create(name="3")
        rows_affected = await Tournament.all().update(name="2")
        self.assertEqual(rows_affected, 2)

        tournament = await Tournament.first()
        self.assertEqual(tournament.name, "2")

    async def test_update_auto_now(self):
        obj = await DefaultUpdate.create()

        now = datetime.now()
        updated_at = now - timedelta(days=1)
        await DefaultUpdate.filter(pk=obj.pk).update(updated_at=updated_at)

        obj1 = await DefaultUpdate.get(pk=obj.pk)
        self.assertEqual(obj1.updated_at.date(), updated_at.date())

    async def test_update_relation(self):
        tournament_first = await Tournament.create(name="1")
        tournament_second = await Tournament.create(name="2")

        await Event.create(name="1", tournament=tournament_first)
        await Event.all().update(tournament=tournament_second)
        event = await Event.first()
        self.assertEqual(event.tournament_id, tournament_second.id)

    @test.requireCapability(dialect="mysql")
    @test.requireCapability(dialect="sqlite")
    async def test_update_with_custom_function(self):
        class JsonSet(Function):
            def __init__(self, field: F, expression: str, value: Any):
                super().__init__("JSON_SET", field, expression, value)

        json = await JSONFields.create(data={})
        self.assertEqual(json.data_default, {"a": 1})

        json.data_default = JsonSet(F("data_default"), "$.a", 2)
        await json.save()

        json_update = await JSONFields.get(pk=json.pk)
        self.assertEqual(json_update.data_default, {"a": 2})

        await JSONFields.filter(pk=json.pk).update(
            data_default=JsonSet(F("data_default"), "$.a", 3)
        )
        json_update = await JSONFields.get(pk=json.pk)
        self.assertEqual(json_update.data_default, {"a": 3})

    async def test_refresh_from_db(self):
        int_field = await IntFields.create(intnum=1, intnum_null=2)
        int_field_in_db = await IntFields.get(pk=int_field.pk)
        int_field_in_db.intnum = F("intnum") + 1
        await int_field_in_db.save(update_fields=["intnum"])
        self.assertIsNot(int_field_in_db.intnum, 2)
        self.assertIs(int_field_in_db.intnum_null, 2)

        await int_field_in_db.refresh_from_db(fields=["intnum"])
        self.assertIs(int_field_in_db.intnum, 2)
        self.assertIs(int_field_in_db.intnum_null, 2)

        int_field_in_db.intnum = F("intnum") + 1
        await int_field_in_db.save()
        self.assertIsNot(int_field_in_db.intnum, 3)
        self.assertIs(int_field_in_db.intnum_null, 2)

        await int_field_in_db.refresh_from_db()
        self.assertIs(int_field_in_db.intnum, 3)
        self.assertIs(int_field_in_db.intnum_null, 2)
