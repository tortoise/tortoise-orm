from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0007_auto_20260124_1650")]

    initial = False

    operations = [
        ops.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(unique=True, max_length=120)),
            ],
            options={"table": "category", "app": "blog", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.AddField(
            model_name="Post",
            name="categories",
            field=fields.ManyToManyField(
                "blog.Category",
                unique=True,
                db_constraint=True,
                through="post_category",
                forward_key="category_id",
                backward_key="post_id",
                related_name="posts",
                on_delete=OnDelete.CASCADE,
            ),
        ),
    ]
