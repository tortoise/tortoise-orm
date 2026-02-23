from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0024_auto_20260216_1715")]

    initial = False

    operations = [
        ops.RemoveConstraint(
            model_name="Product",
            name="ck_product_price_positive",
            fields=None,
        ),
    ]
