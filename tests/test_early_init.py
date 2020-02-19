from tortoise import Tortoise, fields
from tortoise.contrib import test
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ReverseRelation["Event"]

    class Meta:
        ordering = ["name"]


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    tournament: fields.ForeignKeyNullableRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", null=True
    )

    class Meta:
        ordering = ["name"]


class TestBasic(test.TestCase):
    def test_early_init(self):

        Event_TooEarly = pydantic_model_creator(Event)
        self.assertEqual(
            Event_TooEarly.schema(),
            {
                "title": "Event",
                "type": "object",
                "properties": {
                    "id": {"title": "Id", "type": "integer"},
                    "name": {"title": "Name", "type": "string"},
                    "created_at": {"title": "Created At", "type": "string", "format": "date-time"},
                },
            },
        )

        Tortoise.init_models(["tests.test_early_init"], "models")

        Event_Pydantic = pydantic_model_creator(Event)
        self.assertEqual(
            Event_Pydantic.schema(),
            {
                "title": "Event",
                "type": "object",
                "properties": {
                    "id": {"title": "Id", "type": "integer"},
                    "name": {"title": "Name", "type": "string"},
                    "created_at": {"title": "Created At", "type": "string", "format": "date-time"},
                    "tournament": {
                        "title": "Tournament",
                        "allOf": [{"$ref": "#/definitions/Tournament"}],
                    },
                },
                "definitions": {
                    "Tournament": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "created_at": {
                                "title": "Created At",
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                    }
                },
            },
        )
