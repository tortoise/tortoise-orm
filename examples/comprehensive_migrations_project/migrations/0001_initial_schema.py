from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="Company",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=200)),
                ("code", fields.CharField(unique=True, max_length=50)),
                ("description", fields.TextField(unique=False)),
                (
                    "is_active",
                    fields.BooleanField(default=True, generated=False, null=False, unique=False),
                ),
                ("founded_date", fields.DateField(generated=False, null=False, unique=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "company",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Company entity - represents an organization.",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=150)),
                (
                    "company",
                    fields.ForeignKeyField(
                        "erp.Company",
                        source_field="company_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="departments",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                (
                    "parent",
                    fields.ForeignKeyField(
                        "erp.Department",
                        source_field="parent_id",
                        null=True,
                        db_constraint=True,
                        to_field="id",
                        related_name="subdepartments",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                (
                    "is_active",
                    fields.BooleanField(default=True, generated=False, null=False, unique=False),
                ),
            ],
            options={
                "table": "department",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Department entity - organizational unit within a company.",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Employee",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("first_name", fields.CharField(max_length=100)),
                ("last_name", fields.CharField(max_length=100)),
                ("email", fields.CharField(unique=True, max_length=255)),
                (
                    "department",
                    fields.ForeignKeyField(
                        "erp.Department",
                        source_field="department_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="employees",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("hire_date", fields.DateField(generated=False, null=False, unique=False)),
                (
                    "is_active",
                    fields.BooleanField(default=True, generated=False, null=False, unique=False),
                ),
            ],
            options={
                "table": "employee",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Employee entity - person working for the company.",
            },
            bases=["Model"],
        ),
    ]
