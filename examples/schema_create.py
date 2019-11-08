"""
This example demonstrates SQL Schema generation for each DB type supported.
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model
from tortoise.utils import get_schema_sql


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, description="Tournament name", index=True)
    created = fields.DatetimeField(auto_now_add=True, description="Created datetime")

    events: fields.ReverseRelation["Event"]

    class Meta:
        table_description = "What Tournaments we have"


class Event(Model):
    id = fields.IntField(pk=True, description="Event ID")
    name = fields.CharField(max_length=255, unique=True)
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", description="FK to tournament"
    )
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team",
        related_name="events",
        through="event_team",
        description="How participants relate",
    )
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    token = fields.CharField(max_length=100, description="Unique token", unique=True)

    class Meta:
        table_description = "This table contains a list of all the events"


class Team(Model):
    name = fields.CharField(max_length=50, pk=True, description="The TEAM name (and PK)")

    events: fields.ManyToManyRelation[Event]

    class Meta:
        table_description = "The TEAMS!"


async def run():
    print("SQLite:\n")
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
    print(sql)

    print("\n\nMySQL:\n")
    await Tortoise.init(db_url="mysql://root:@127.0.0.1:3306/", modules={"models": ["__main__"]})
    sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
    print(sql)

    print("\n\nPostgreSQL:\n")
    await Tortoise.init(
        db_url="postgres://postgres:@127.0.0.1:5432/", modules={"models": ["__main__"]}
    )
    sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
    print(sql)


if __name__ == "__main__":
    run_async(run())
