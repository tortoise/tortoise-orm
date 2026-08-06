"""Data migration to populate computed fields from source data."""

from decimal import Decimal

from tortoise import migrations
from tortoise.migrations import operations as ops

_CONCAT_SQL = {
    "postgres": "UPDATE employee SET full_name = first_name || ' ' || last_name WHERE full_name IS NULL",
    "sqlite": "UPDATE employee SET full_name = first_name || ' ' || last_name WHERE full_name IS NULL",
    "mysql": "UPDATE employee SET full_name = CONCAT(first_name, ' ', last_name) WHERE full_name IS NULL",
    "mssql": "UPDATE employee SET full_name = first_name + ' ' + last_name WHERE full_name IS NULL",
}


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


def populate_full_name(apps, schema_editor):
    """Populate full_name from first_name + last_name using dialect-specific SQL."""
    sql = _CONCAT_SQL[schema_editor.DIALECT]

    async def do_populate():
        await schema_editor.client.execute_query(sql)

    return do_populate()


def clear_full_name(apps, schema_editor):
    """Reverse: Clear full_name field."""

    async def do_clear():
        await schema_editor.client.execute_query("UPDATE employee SET full_name = NULL")

    return do_clear()


class Migration(migrations.Migration):
    dependencies = [("erp", "0010_add_computed_fields")]

    initial = False

    operations = [
        ops.RunPython(
            code=populate_total_amount,
            reverse_code=clear_total_amount,
        ),
        ops.RunPython(
            code=populate_full_name,
            reverse_code=clear_full_name,
        ),
    ]
