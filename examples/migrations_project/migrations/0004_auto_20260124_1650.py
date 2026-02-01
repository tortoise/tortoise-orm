from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0003_auto_20260124_1650")]

    initial = False

    operations = [
        ops.CreateModel(
            name="Comment",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                (
                    "post",
                    fields.ForeignKeyField(
                        "blog.Post",
                        source_field="post_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="comments",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("content", fields.TextField(unique=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={"table": "comment", "app": "blog", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
