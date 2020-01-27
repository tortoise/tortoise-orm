"""
This example demonstrates pydantic serialisation
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model
from tortoise.pydantic import pydantic_model_creator


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    # events: fields.ReverseRelation["Event"]

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events"
    )
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team"
    )
    address: fields.OneToOneNullableRelation["Address"]

    def __str__(self):
        return self.name


class Address(Model):
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event", on_delete=fields.CASCADE, related_name="address", pk=True
    )

    def __str__(self):
        return f"Address({self.city}, {self.street})"


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    # events: fields.ManyToManyRelation[Event]

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    Event_Pydantic = pydantic_model_creator(Event)
    print(Event_Pydantic.schema_json(indent=4))

    tournament = Tournament(name="New Tournament")
    await tournament.save()
    await Event(name="Without participants", tournament_id=tournament.id).save()
    event = Event(name="Test", tournament_id=tournament.id)
    await event.save()

    await Address.create(city="Santa Monica", street="Ocean", event=event)

    p = await Event_Pydantic.from_tortoise(await Event.all().first())
    print(p.dict())


if __name__ == "__main__":
    run_async(run())
