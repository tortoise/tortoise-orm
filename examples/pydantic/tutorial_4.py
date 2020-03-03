"""
Pydantic tutorial 4

Here we introduce:
* Configuring model creator via PydanticMeta class.
* Using callable functions to annotate extra data.
"""
from tortoise import Tortoise, fields, run_async
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import NoValuesFetched
from tortoise.models import Model


class Tournament(Model):
    """
    This references a Tournament
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    #: The date-time the Tournament record was created at
    created_at = fields.DatetimeField(auto_now_add=True)

    def name_length(self) -> int:
        """
        Computes length of name
        """
        # Note that this function needs to be annotated with a return type so that pydantic
        #  can generate a valid schema
        return len(self.name)

    def events_num(self) -> int:
        """
        Computes team size.
        """
        # Note that this function needs to be annotated with a return type so that pydantic
        #  can generate a valid schema.

        # Note that the pydantic serializer can't call async methods, but the tortoise helpers
        #  pre-fetch relational data, so that it is available before serialization. So we don't
        #  need to await the relation. We do however have to protect against the case where no
        #  prefetching was done, hence catching and handling the
        #  ``tortoise.exceptions.NoValuesFetched`` exception.
        try:
            return len(self.events)
        except NoValuesFetched:
            return -1

    class PydanticMeta:
        exclude = ("created_at",)
        computed = ("name_length", "events_num")


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

    class Meta:
        # Define the default ordering
        #  the pydantic serialiser will use this to order the results
        ordering = ["name"]

    class PydanticMeta:
        exclude = ("created_at",)


# Initialise model structure early. This does not init any database structures
Tortoise.init_models(["__main__"], "models")


# We now have a complete model
Tournament_Pydantic = pydantic_model_creator(Tournament)
# Print JSON-schema
print(Tournament_Pydantic.schema_json(indent=4))


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    # Create objects
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Event 1", tournament=tournament)
    await Event.create(name="Event 2", tournament=tournament)

    # Serialise Tournament
    tourpy = await Tournament_Pydantic.from_tortoise_orm(tournament)

    # As serialised JSON
    print(tourpy.json(indent=4))


if __name__ == "__main__":
    run_async(run())
