from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0011_auto_20260124_1651")]

    initial = False

    operations = [
        ops.RenameModel(old_name="Status", new_name="State"),
    ]
