from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="Order",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("number", fields.CharField(unique=True, max_length=40)),
                ("status", fields.CharField(max_length=20)),
            ],
            options={"table": "orders_order", "app": "orders", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="OrderItem",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                (
                    "order",
                    fields.ForeignKeyField(
                        "orders.Order",
                        source_field="order_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="items",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("quantity", fields.IntField()),
            ],
            options={"table": "orders_order_item", "app": "orders", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
