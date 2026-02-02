from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0010_auto_20260124_1651")]

    initial = False

    operations = [
        ops.CreateModel(
            name="Status",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("code", fields.CharField(unique=True, max_length=20)),
            ],
            options={"table": "status", "app": "blog", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
