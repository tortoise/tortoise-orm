"""
This example demonstrates pydantic serialisation, and how to use early partial init.
"""
from tortoise import Tortoise, fields
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


Event_TooEarly = pydantic_model_creator(Event)
print("Relations are missing if models not initialized:")
print(Event_TooEarly.schema_json(indent=4))


Tortoise.init_models(["__main__"], "models")

Event_Pydantic = pydantic_model_creator(Event)
print("\nRelations are now present:")
print(Event_Pydantic.schema_json(indent=4))

# Now we can use the pydantic model early if needed
