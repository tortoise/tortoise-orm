"""
This example demonstrates pydantic serialisation
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model
from tortoise.pydantic import pydantic_model_creator


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ReverseRelation["Event"]

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    tournament: fields.ForeignKeyNullableRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", null=True
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
    created_at = fields.DatetimeField(auto_now_add=True)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event", on_delete=fields.CASCADE, related_name="address", pk=True
    )

    def __str__(self):
        return f"Address({self.city}, {self.street})"


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ManyToManyRelation[Event]

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    Event_Pydantic = pydantic_model_creator(Event)
    Tournament_Pydantic = pydantic_model_creator(Tournament)
    Team_Pydantic = pydantic_model_creator(Team)
    # print(Event_Pydantic.schema_json(indent=4))
    # print(Tournament_Pydantic.schema_json(indent=4))
    # print(Team_Pydantic.schema_json(indent=4))

    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Empty")
    event = await Event.create(name="Test", tournament=tournament)
    await Address.create(city="Santa Monica", street="Ocean", event=event)
    team1 = await Team.create(name="Onesies")
    team2 = await Team.create(name="T-Shirts")
    await event.participants.add(team1, team2)

    pl = [(await Event_Pydantic.from_tortoise_orm(e)).dict() for e in await Event.all()]
    print(
        Event_Pydantic.__config__.json_dumps(pl, default=Event_Pydantic.__json_encoder__, indent=4)
    )

    p = await Tournament_Pydantic.from_tortoise_orm(await Tournament.all().first())
    print(p.json(indent=4))

    p = await Team_Pydantic.from_tortoise_orm(await Team.all().first())
    print(p.json(indent=4))


if __name__ == "__main__":
    run_async(run())
