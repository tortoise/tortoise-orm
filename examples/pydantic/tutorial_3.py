"""
Pydantic tutorial 3

Here we introduce:
* Relationships
* Early model init
"""
from tortoise import Tortoise, fields, run_async
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Tournament(Model):
    """
    This references a Tournament
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    #: The date-time the Tournament record was created at
    created_at = fields.DatetimeField(auto_now_add=True)


class Event(Model):
    """
    This references an Event in a Tournament
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)

    tournament = fields.ForeignKeyField(
        "models.Tournament", related_name="events", description="The Tournement this happens in"
    )


# Early model, does not include relations
Tournament_Pydantic_Early = pydantic_model_creator(Tournament)
# Print JSON-schema
print(Tournament_Pydantic_Early.schema_json(indent=4))


# Initialise model structure early. This does not init any database structures
Tortoise.init_models(["__main__"], "models")


# We now have a complete model
Tournament_Pydantic = pydantic_model_creator(Tournament)
# Print JSON-schema
print(Tournament_Pydantic.schema_json(indent=4))

# Note how both schema's don't follow relations back.
Event_Pydantic = pydantic_model_creator(Event)
# Print JSON-schema
print(Event_Pydantic.schema_json(indent=4))


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    # Create objects
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="The Event", tournament=tournament)

    # Serialise Tournament
    tourpy = await Tournament_Pydantic.from_tortoise_orm(tournament)

    # As serialised JSON
    print(tourpy.json(indent=4))

    # Serialise Event
    eventpy = await Event_Pydantic.from_tortoise_orm(event)

    # As serialised JSON
    print(eventpy.json(indent=4))


if __name__ == "__main__":
    run_async(run())
