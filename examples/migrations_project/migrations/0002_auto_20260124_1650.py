from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('blog', '0001_initial')]

    initial = False

    operations = [
        ops.AddField(
            model_name='Post',
            name='slug',
            field=fields.CharField(unique=True, max_length=220),
        ),
    ]
