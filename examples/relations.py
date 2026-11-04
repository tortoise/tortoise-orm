"""
This example shows how relations between models work.

Key points in this example are use of ForeignKeyField and ManyToManyField
to declare relations and use of .prefetch_related() and .fetch_related()
to get this related objects
"""

from tortoise import fields
from tortoise.exceptions import NoValuesFetched
from tortoise.expressions import Subquery
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()

    events: fields.ReverseRelation["Event"]

    def __str__(self) -> str:
        return self.name


class Event(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
        Tournament, related_name="events"
    )
    # class Team does not defined before Event, so we have to use '{app}.{model_class}'
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team"
    )

    tournament_id: int
    address: fields.BackwardOneToOneRelation["Address"]

    def __str__(self) -> str:
        return self.name


class Address(Model):
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        Event, on_delete=fields.OnDelete.CASCADE, related_name="address", primary_key=True
    )
    event_id: int

    def __str__(self) -> str:
        return f"Address({self.city}, {self.street})"


class Team(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()

    events: fields.ManyToManyRelation[Event]

    def __str__(self) -> str:
        return self.name


async def run() -> None:
    tournament = Tournament(name="New Tournament")
    await tournament.save()
    await Event(name="Without participants", tournament_id=tournament.id).save()
    event = Event(name="Test", tournament_id=tournament.id)
    await event.save()

    await Address.create(city="Santa Monica", street="Ocean", event=event)

    participants = []
    for i in range(2):
        team = Team(name=f"Team {(i + 1)}")
        await team.save()
        participants.append(team)
    await event.participants.add(participants[0], participants[1])
    await event.participants.add(participants[0], participants[1])

    try:
        for team in event.participants:
            print(team.id)
    except NoValuesFetched:
        pass

    async for team in event.participants:
        print(team.id)

    for team in event.participants:
        print(team.id)

    print(
        await Event.filter(participants=participants[0].id).prefetch_related(
            "participants", "tournament"
        )
    )

    await participants[0].fetch_related("events")
    print(list(participants[0].events))

    await Team.fetch_for_list(participants, "events")
    for team in participants:
        print(team.name, list(team.events))

    print(await Team.filter(events__tournament__id=tournament.id))

    print(await Event.filter(tournament=tournament))

    print(await Event.filter(tournament__in=[tournament]))

    print(await Event.filter(address__city__in=Subquery(Address.all().values("city"))))

    print(await Tournament.filter(events__in=[event]))

    print(
        await Tournament.filter(events__name__in=["Test", "Prod"])
        .order_by("-events__participants__name")
        .distinct()
    )

    print(await Event.filter(id=event.id).values("id", "name", tournament="tournament__name"))

    print(await Event.filter(id=event.id).values_list("id", "participants__name"))

    print(await Address.filter(event=event).first())

    event_reload1 = await Event.filter(id=event.id).get()
    print(await event_reload1.address)

    event_reload2 = await Event.filter(id=event.id).prefetch_related("address").get()
    print(event_reload2.address)

    print(dict(await event_reload2.address.event))


if __name__ == "__main__":
    from tortoise.contrib.test import run_in_memory_sqlite

    run_in_memory_sqlite(run)
