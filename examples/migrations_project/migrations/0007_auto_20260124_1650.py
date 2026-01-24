from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0006_auto_20260124_1650")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Post",
            name="body",
            field=fields.TextField(source_field="content", unique=False),
        ),
        ops.AlterField(
            model_name="Post",
            name="title",
            field=fields.CharField(max_length=300),
        ),
    ]
