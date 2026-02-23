from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0006_alter_field_types")]

    initial = False

    operations = [
        ops.AddField(
            model_name="Company",
            name="temporary_notes",
            field=fields.TextField(null=True, unique=False),
        ),
        ops.AddField(
            model_name="Department",
            name="legacy_code",
            field=fields.CharField(null=True, max_length=50),
        ),
        ops.AddField(
            model_name="Employee",
            name="temp_status",
            field=fields.CharField(null=True, max_length=20),
        ),
    ]
