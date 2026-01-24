from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="Author",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=200)),
            ],
            options={"table": "author", "app": "blog", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Post",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("title", fields.CharField(max_length=200)),
                ("content", fields.TextField(unique=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
                (
                    "author",
                    fields.ForeignKeyField(
                        "blog.Author",
                        source_field="author_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="posts",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
            ],
            options={"table": "post", "app": "blog", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
