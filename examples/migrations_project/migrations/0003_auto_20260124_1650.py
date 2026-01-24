from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('blog', '0002_auto_20260124_1650')]

    initial = False

    operations = [
        ops.AddField(
            model_name='Post',
            name='published_at',
            field=fields.DatetimeField(null=True, auto_now=False, auto_now_add=False),
        ),
    ]
