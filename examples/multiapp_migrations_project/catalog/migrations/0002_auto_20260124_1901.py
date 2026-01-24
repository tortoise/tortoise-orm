from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial'), ('catalog', '0001_initial')]

    initial = False

    operations = [
        ops.AddField(
            model_name='Product',
            name='owner',
            field=fields.ForeignKeyField('accounts.User', source_field='owner_id', null=True, db_constraint=True, to_field='id', related_name='owned_products', on_delete=OnDelete.CASCADE),
        ),
    ]
