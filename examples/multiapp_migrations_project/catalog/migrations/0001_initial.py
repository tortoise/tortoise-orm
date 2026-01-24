from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("sku", fields.CharField(unique=True, max_length=32)),
                ("name", fields.CharField(max_length=150)),
                ("price_cents", fields.IntField()),
            ],
            options={"table": "catalog_product", "app": "catalog", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
