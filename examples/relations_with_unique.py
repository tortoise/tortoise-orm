"""
This example shows how relations between models work.

Key points in this example are use of ForeignKeyField and ManyToManyField
to declare relations and use of .prefetch_related() and .fetch_related()
to get this related objects
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(uk=True)
    name = fields.CharField(max_length=100, pk=True)

    events: fields.ReverseRelation["Event"]

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", to_field="name",
    )

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    tournament = Tournament(id=1, name="New Tournament")
    await tournament.save()
    await Event(name="Without participants", tournament_id=tournament.name).save()


if __name__ == "__main__":
    run_async(run())
