from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0008_auto_20260124_1650")]

    initial = False

    operations = [
        ops.RemoveField(model_name="Post", name="published_at"),
    ]
