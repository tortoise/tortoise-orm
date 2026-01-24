from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0005_auto_20260124_1650")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Author",
            name="full_name",
            field=fields.CharField(source_field="name", max_length=200),
        ),
        ops.RenameField(
            model_name="Post",
            old_name="content",
            new_name="body",
        ),
    ]
