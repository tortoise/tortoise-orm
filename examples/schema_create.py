import asyncio
import binascii
import os

from tortoise import Tortoise, fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.name


def generate_token():
    return binascii.hexlify(os.urandom(16)).decode("ascii")


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField(unique=True)
    tournament = fields.ForeignKeyField("models.Tournament", related_name="events")
    participants = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team"
    )
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    token = fields.TextField(default=generate_token)

    def __str__(self):
        return self.name


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField(source_field="title")

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(config_file="config.json")
    await Tortoise.generate_schemas()

    tournament = await Tournament.create(name="Test")

    event = await Event.create(name="Test 1", tournament=tournament, prize=100)
    print(event.modified)
    event.name = "Test 2"
    await event.save()
    print(event.modified)

    await Team.create(name="test")
    print(await Team.all().values("name"))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
