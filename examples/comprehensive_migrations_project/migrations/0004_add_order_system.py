from orjson import loads

from examples.comprehensive_migrations_project.models import OrderStatus, PaymentMethod
from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.fields.data import JSON_DUMPS
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0003_add_product_fields")]

    initial = False

    operations = [
        ops.CreateModel(
            name="EmployeeProfile",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                (
                    "employee",
                    fields.OneToOneField(
                        "erp.Employee",
                        source_field="employee_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="profile",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("bio", fields.TextField(null=True, unique=False)),
                ("avatar_hash", fields.BinaryField(null=True, generated=False, unique=False)),
                ("settings", fields.JSONField(null=True, encoder=JSON_DUMPS, decoder=loads)),
            ],
            options={
                "table": "employeeprofile",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Employee profile - demonstrates OneToOneField.",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Order",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("order_number", fields.CharField(unique=True, max_length=50)),
                ("customer_email", fields.CharField(max_length=255)),
                ("total_cents", fields.BigIntField()),
                (  # type: ignore[list-item]
                    "status",
                    fields.IntEnumField(
                        default=OrderStatus.PENDING,
                        description="PENDING: 1\nPROCESSING: 2\nSHIPPED: 3\nDELIVERED: 4\nCANCELLED: 5",
                        enum_type=OrderStatus,
                        generated=False,
                    ),
                ),
                (  # type: ignore[list-item]
                    "payment_method",
                    fields.CharEnumField(
                        description="CREDIT_CARD: credit_card\nPAYPAL: paypal\nBANK_TRANSFER: bank_transfer\nCASH: cash",
                        enum_type=PaymentMethod,
                        max_length=13,
                    ),
                ),
                (
                    "products",
                    fields.ManyToManyField(
                        "erp.Product",
                        unique=True,
                        db_constraint=True,
                        through="order_product",
                        forward_key="product_id",
                        backward_key="order_id",
                        related_name="orders",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("digital_signature", fields.BinaryField(null=True, generated=False, unique=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ("updated_at", fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={
                "table": "order",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Order entity - customer orders demonstrating M2M and enum fields.",
            },
            bases=["Model"],
        ),
    ]
