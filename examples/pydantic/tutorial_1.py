"""
Pydantic tutorial 1
"""
from tortoise import Tortoise, fields, run_async
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)


Tournament_Pydantic = pydantic_model_creator(Tournament)
# Print JSON-schema
print(Tournament_Pydantic.schema_json(indent=4))


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    # Create object
    tournament = await Tournament.create(name="New Tournament")
    # Serialise it
    tourpy = await Tournament_Pydantic.from_tortoise_orm(tournament)

    # As Python dict with Python objects (e.g. datetime)
    print(tourpy.dict())
    # As serialised JSON (e.g. datetime is ISO8601 string representation)
    print(tourpy.json(indent=4))


if __name__ == "__main__":
    run_async(run())

