from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=100)),
            ],
            options={"table": "accounts_team", "app": "accounts", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=100)),
                ("email", fields.CharField(unique=True, max_length=200)),
                (
                    "team",
                    fields.ForeignKeyField(
                        "accounts.Team",
                        source_field="team_id",
                        null=True,
                        db_constraint=True,
                        to_field="id",
                        related_name="members",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
            ],
            options={"table": "accounts_user", "app": "accounts", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
