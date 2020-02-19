"""
This example demonstrates pydantic serialisation
"""
from tortoise import Tortoise, fields, run_async
from tortoise.contrib.pydantic import pydantic_model_creator, pydantic_queryset_creator
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
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team"
    )
    address: fields.OneToOneNullableRelation["Address"]

    class Meta:
        ordering = ["name"]


class Address(Model):
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)
    created_at = fields.DatetimeField(auto_now_add=True)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event", on_delete=fields.CASCADE, related_name="address", pk=True
    )

    class Meta:
        ordering = ["city"]


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ManyToManyRelation[Event]

    class Meta:
        ordering = ["name"]


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    Event_Pydantic = pydantic_model_creator(Event)
    Event_Pydantic_List = pydantic_queryset_creator(Event)
    Tournament_Pydantic = pydantic_model_creator(Tournament)
    Team_Pydantic = pydantic_model_creator(Team)

    # print(Event_Pydantic_List.schema_json(indent=4))
    # print(Event_Pydantic.schema_json(indent=4))
    # print(Tournament_Pydantic.schema_json(indent=4))
    # print(Team_Pydantic.schema_json(indent=4))

    tournament = await Tournament.create(name="New Tournament")
    tournament2 = await Tournament.create(name="Old Tournament")
    await Event.create(name="Empty")
    event = await Event.create(name="Test", tournament=tournament)
    event2 = await Event.create(name="TestLast", tournament=tournament)
    event3 = await Event.create(name="Test2", tournament=tournament2)
    await Address.create(city="Santa Monica", street="Ocean", event=event)
    await Address.create(city="Somewhere Else", street="Lane", event=event2)
    team1 = await Team.create(name="Onesies")
    team2 = await Team.create(name="T-Shirts")
    team3 = await Team.create(name="Alternates")
    await event.participants.add(team1, team2, team3)
    await event2.participants.add(team1, team2)
    await event3.participants.add(team1, team3)

    p = await Event_Pydantic.from_tortoise_orm(await Event.get(name="Test"))
    print("One Event:", p.json(indent=4))

    p = await Tournament_Pydantic.from_tortoise_orm(await Tournament.get(name="New Tournament"))
    print("One Tournament:", p.json(indent=4))

    p = await Team_Pydantic.from_tortoise_orm(await Team.get(name="Onesies"))
    print("One Team:", p.json(indent=4))

    pl = await Event_Pydantic_List.from_queryset(Event.filter(address__event_id__isnull=True))
    print("All Events without addresses:", pl.json(indent=4))


if __name__ == "__main__":
    run_async(run())
