from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.indexes import Index
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import UniqueConstraint


class Migration(migrations.Migration):
    dependencies = [("erp", "0012_require_computed_fields")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Department",
            name="parent",
            field=fields.ForeignKeyField(
                "erp.Department",
                source_field="parent_id",
                null=True,
                db_index=True,
                db_constraint=True,
                to_field="id",
                related_name="subdepartments",
                on_delete=OnDelete.CASCADE,
            ),
        ),
        ops.AddConstraint(
            model_name="Employee",
            constraint=UniqueConstraint(fields=("email", "department_id"), name=None),
        ),
        ops.AlterField(
            model_name="Order",
            name="customer_email",
            field=fields.CharField(db_index=True, max_length=255),
        ),
        ops.AddIndex(
            model_name="Product",
            index=Index(fields=["category_id", "is_active"], name="idx_product_category_active"),
        ),
    ]
