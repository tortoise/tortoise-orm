from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0015_add_audit_log_remove_index")]

    initial = False

    operations = [
        ops.DeleteModel(name="AuditLog"),
    ]
