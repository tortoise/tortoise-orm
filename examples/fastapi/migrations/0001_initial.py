from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="Users",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                (
                    "username",
                    fields.CharField(unique=True, description="This is a username", max_length=20),
                ),
                ("name", fields.CharField(null=True, max_length=50)),
                ("family_name", fields.CharField(null=True, max_length=50)),
                ("category", fields.CharField(default="misc", max_length=30)),
                ("password_hash", fields.CharField(null=True, max_length=128)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ("modified_at", fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={
                "table": "users",
                "app": "models",
                "pk_attr": "id",
                "table_description": "The User model",
            },
            bases=["Model"],
        ),
    ]
