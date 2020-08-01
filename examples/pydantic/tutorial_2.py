"""
Pydantic tutorial 2

Here we introduce:
* Creating a list-model to serialise a queryset
* Default sorting is honoured
"""
from tortoise import Tortoise, fields, run_async
from tortoise.contrib.pydantic import pydantic_queryset_creator
from tortoise.models import Model


class Tournament(Model):
    """
    This references a Tournament
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    #: The date-time the Tournament record was created at
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        # Define the default ordering
        #  the pydantic serialiser will use this to order the results
        ordering = ["name"]


# Create a list of models for population from a queryset.
Tournament_Pydantic_List = pydantic_queryset_creator(Tournament)
# Print JSON-schema
print(Tournament_Pydantic_List.schema_json(indent=4))


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    # Create objects
    await Tournament.create(name="New Tournament")
    await Tournament.create(name="Another")
    await Tournament.create(name="Last Tournament")

    # Serialise it
    tourpy = await Tournament_Pydantic_List.from_queryset(Tournament.all())

    # As Python dict with Python objects (e.g. datetime)
    # Note that the root element is '__root__' that contains the root element.
    print(tourpy.dict())
    # As serialised JSON (e.g. datetime is ISO8601 string representation)
    print(tourpy.json(indent=4))


if __name__ == "__main__":
    run_async(run())
