from tortoise import Tortoise, fields, run_async
from tortoise.models import Model
from tortoise.query_utils import Prefetch


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    events: fields.ReverseRelation["Event"]

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

    def __str__(self):
        return self.name


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    events: fields.ManyToManyRelation[Event]

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    tournament = await Tournament.create(name="tournament")
    await Event.create(name="First", tournament=tournament)
    await Event.create(name="Second", tournament=tournament)
    tournament_with_filtered = (
        await Tournament.all()
        .prefetch_related(Prefetch("events", queryset=Event.filter(name="First")))
        .first()
    )
    print(tournament_with_filtered)
    print(await Tournament.first().prefetch_related("events"))

    tournament_with_filtered_to_attr = (
        await Tournament.all()
        .prefetch_related(
            Prefetch("events", queryset=Event.filter(name="First"), to_attr="to_attr_events_first"),
            Prefetch(
                "events", queryset=Event.filter(name="Second"), to_attr="to_attr_events_second"
            ),
        )
        .first()
    )
    print(tournament_with_filtered_to_attr.to_attr_events_first)
    print(tournament_with_filtered_to_attr.to_attr_events_second)


if __name__ == "__main__":
    run_async(run())
