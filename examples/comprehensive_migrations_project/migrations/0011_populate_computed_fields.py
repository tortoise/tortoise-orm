"""Data migration to populate computed fields from source data."""

from decimal import Decimal

from tortoise import migrations
from tortoise.migrations import operations as ops


def populate_total_amount(apps, schema_editor):
    """Convert total_cents to total_amount (cents to dollars)."""
    Order = apps.get_model("erp", "Order")

    async def do_populate():
        async for order in Order.all():
            order.total_amount = Decimal(order.total_cents) / Decimal(100)
            await order.save(update_fields=["total_amount"])

    return do_populate()


def clear_total_amount(apps, schema_editor):
    """Reverse: Clear total_amount field."""
    Order = apps.get_model("erp", "Order")

    async def do_clear():
        async for order in Order.all():
            order.total_amount = None
            await order.save(update_fields=["total_amount"])

    return do_clear()


class Migration(migrations.Migration):
    dependencies = [("erp", "0010_add_computed_fields")]

    initial = False

    operations = [
        ops.RunPython(
            code=populate_total_amount,
            reverse_code=clear_total_amount,
        ),
        ops.RunSQL(
            sql="UPDATE employee SET full_name = first_name || ' ' || last_name WHERE full_name IS NULL",
            reverse_sql="UPDATE employee SET full_name = NULL",
        ),
    ]
