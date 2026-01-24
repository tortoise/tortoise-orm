from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("blog", "0013_add_post_summary")]

    initial = False

    operations = [
        ops.RenameField(
            model_name="Post",
            old_name="summary",
            new_name="excerpt",
        ),
    ]
