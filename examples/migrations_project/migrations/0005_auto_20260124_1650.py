from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0004_auto_20260124_1650")]

    initial = False

    operations = [
        ops.RenameField(
            model_name="Author",
            old_name="name",
            new_name="full_name",
        ),
    ]
