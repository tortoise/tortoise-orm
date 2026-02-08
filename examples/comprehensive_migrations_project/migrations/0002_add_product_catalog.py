from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0001_initial_schema")]

    initial = False

    operations = [
        ops.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(unique=True, max_length=100)),
                ("description", fields.TextField(null=True, unique=False)),
                (
                    "parent",
                    fields.ForeignKeyField(
                        "erp.Category",
                        source_field="parent_id",
                        null=True,
                        db_constraint=True,
                        to_field="id",
                        related_name="subcategories",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("priority", fields.SmallIntField(default=0)),
            ],
            options={
                "table": "category",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Category entity - hierarchical product categorization.",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("sku", fields.CharField(unique=True, max_length=50)),
                ("name", fields.CharField(max_length=200)),
                ("description", fields.TextField(unique=False)),
                (
                    "category",
                    fields.ForeignKeyField(
                        "erp.Category",
                        source_field="category_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="products",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                (
                    "is_active",
                    fields.BooleanField(default=True, generated=False, null=False, unique=False),
                ),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "product",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Product entity - items offered by the company.",
            },
            bases=["Model"],
        ),
    ]
