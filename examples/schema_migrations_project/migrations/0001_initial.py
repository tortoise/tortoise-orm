from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateSchema(schema_name="catalog"),
        ops.CreateSchema(schema_name="warehouse"),
        ops.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(unique=True, max_length=120)),
            ],
            options={"table": "category", "schema": "catalog", "app": "shop", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Supplier",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=200)),
                ("contact_email", fields.CharField(null=True, max_length=254)),
            ],
            options={"table": "supplier", "schema": "warehouse", "app": "shop", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=200)),
                ("sku", fields.CharField(unique=True, max_length=40)),
                ("price", fields.DecimalField(max_digits=10, decimal_places=2)),
                (
                    "category",
                    fields.ForeignKeyField(
                        "shop.Category",
                        source_field="category_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="products",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                (
                    "suppliers",
                    fields.ManyToManyField(
                        "shop.Supplier",
                        unique=True,
                        db_constraint=True,
                        through="product_supplier",
                        forward_key="supplier_id",
                        backward_key="product_id",
                        related_name="products",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
            ],
            options={"table": "product", "schema": "catalog", "app": "shop", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Inventory",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("quantity", fields.IntField(default=0)),
                (
                    "product",
                    fields.ForeignKeyField(
                        "shop.Product",
                        source_field="product_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="stock_entries",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                (
                    "supplier",
                    fields.ForeignKeyField(
                        "shop.Supplier",
                        source_field="supplier_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="stock_entries",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
            ],
            options={"table": "inventory", "schema": "warehouse", "app": "shop", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
