from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0009_auto_20260124_1651")]

    initial = False

    operations = [
        ops.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(unique=True, max_length=80)),
            ],
            options={"table": "tag", "app": "blog", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.AddField(
            model_name="Post",
            name="tags",
            field=fields.ManyToManyField(
                "blog.Tag",
                unique=True,
                db_constraint=True,
                through="post_tag",
                forward_key="tag_id",
                backward_key="post_id",
                related_name="posts",
                on_delete=OnDelete.CASCADE,
            ),
        ),
    ]
