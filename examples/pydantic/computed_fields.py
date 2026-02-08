"""
Pydantic computed fields example

Here we demonstrate:
* Nullable FK fields become Optional in the Pydantic schema (with ``"default": null``).
* Computed fields that access reverse relations work when the relation is included.
* Computed fields still work when the relation is excluded but manually prefetched.
* NoValuesFetched error propagation when a computed field accesses an unfetched relation.
* Graceful handling pattern using try/except inside the computed function.
"""

import json

from pydantic_core import PydanticSerializationError

from tortoise import Tortoise, fields, run_async
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import NoValuesFetched
from tortoise.models import Model


class Department(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)

    # Define reverse relation for type checking and auto completion
    employees: fields.ReverseRelation["Employee"]

    def employee_count(self) -> int:
        """
        Counts employees in the department.

        Uses try/except to gracefully handle the case where the relation has not been
        fetched, returning 0 instead of raising an error.
        """
        try:
            return len(self.employees)
        except (NoValuesFetched, AttributeError):
            return 0

    def employee_names(self) -> str:
        """
        Returns a comma-separated list of employee names.

        Does NOT handle NoValuesFetched -- demonstrates error propagation when the
        relation has not been fetched.
        """
        return ", ".join(e.name for e in self.employees)

    class PydanticMeta:
        computed = ("employee_count", "employee_names")


class Employee(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)

    department: fields.ForeignKeyNullableRelation[Department] = fields.ForeignKeyField(
        "models.Department", related_name="employees", null=True
    )


# Initialise model structure early so we can create pydantic models at module level
Tortoise.init_models(["__main__"], "models")


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    # Create test data
    engineering = await Department.create(name="Engineering")
    await Employee.create(name="Alice", department=engineering)
    await Employee.create(name="Bob", department=engineering)
    await Employee.create(name="Charlie")  # no department (nullable FK)

    # ──────────────────────────────────────────────────────────────────────
    # Section 1: Nullable FK is Optional in the Pydantic schema
    #
    # A nullable ForeignKeyField generates a pydantic field with
    # "default": null that is NOT in "required".
    # ──────────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("Section 1: Nullable FK is Optional")
    print("=" * 70)

    Employee_Pydantic = pydantic_model_creator(Employee)
    schema = Employee_Pydantic.model_json_schema()
    print(json.dumps(schema, indent=4))

    # The 'department' field has "default": null and is NOT in "required"
    required = schema.get("required", [])
    print(f"\nRequired fields: {required}")
    print("'department' in required:", "department" in required)

    dept_props = schema.get("properties", {}).get("department", {})
    has_default_null = dept_props.get("default") is None and "default" in dept_props
    print(f"'department' has default null: {has_default_null}")

    # ──────────────────────────────────────────────────────────────────────
    # Section 2: Computed field with included relation (auto-prefetched)
    #
    # When the 'employees' reverse relation is included in the pydantic
    # model, from_tortoise_orm() auto-prefetches it. Both computed fields
    # work because the relation data is available.
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Section 2: Computed field with included relation")
    print("=" * 70)

    Department_Pydantic = pydantic_model_creator(Department)

    dept = await Department.get(name="Engineering")
    dept_pydantic = await Department_Pydantic.from_tortoise_orm(dept)
    print(dept_pydantic.model_dump_json(indent=4))

    # Both computed fields work because the relation was auto-prefetched
    print(f"\nemployee_count: {dept_pydantic.employee_count}")
    print(f"employee_names: {dept_pydantic.employee_names}")

    # ──────────────────────────────────────────────────────────────────────
    # Section 3: Computed field with excluded relation + manual prefetch
    #
    # The 'employees' relation is excluded from the pydantic model (so it
    # won't appear in the output), but we manually prefetch it before
    # serialization so the computed fields can still access the data.
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Section 3: Excluded relation + manual prefetch")
    print("=" * 70)

    Department_Pydantic_NoEmployees = pydantic_model_creator(
        Department,
        name="Department_NoEmployees",
        exclude=("employees",),
    )

    dept = await Department.get(name="Engineering")
    # Manually prefetch the relation so computed fields can access it
    await dept.fetch_related("employees")
    dept_pydantic = await Department_Pydantic_NoEmployees.from_tortoise_orm(dept)
    print(dept_pydantic.model_dump_json(indent=4))

    print(f"\nemployee_count: {dept_pydantic.employee_count}")
    print(f"employee_names: {dept_pydantic.employee_names}")

    # ──────────────────────────────────────────────────────────────────────
    # Section 4: NoValuesFetched error propagation
    #
    # Same excluded model but WITHOUT manual prefetch. The employee_names()
    # computed field does not handle NoValuesFetched internally, so the
    # wrapper in creator.py re-raises with a descriptive message during
    # serialization.
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Section 4: NoValuesFetched error propagation")
    print("=" * 70)

    dept = await Department.get(name="Engineering")
    dept_pydantic = await Department_Pydantic_NoEmployees.from_tortoise_orm(dept)
    try:
        # Serialization triggers the computed field, which raises NoValuesFetched
        dept_pydantic.model_dump_json(indent=4)
    except (PydanticSerializationError, NoValuesFetched) as e:
        print(f"Caught error during serialization: {e}")

    # ──────────────────────────────────────────────────────────────────────
    # Section 5: Graceful handling pattern
    #
    # A model with only the graceful computed field (employee_count) that
    # handles NoValuesFetched internally. Even without prefetching, it
    # returns 0 instead of crashing. Contrast with employee_names which
    # would fail in the same scenario.
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Section 5: Graceful handling pattern")
    print("=" * 70)

    # Override PydanticMeta so only the graceful computed field is included
    class GracefulMeta:
        computed = ("employee_count",)

    Department_Pydantic_GracefulOnly = pydantic_model_creator(
        Department,
        name="Department_GracefulOnly",
        exclude=("employees",),
        meta_override=GracefulMeta,
    )

    dept = await Department.get(name="Engineering")
    # No manual prefetch -- employee_count() handles the exception internally
    dept_pydantic = await Department_Pydantic_GracefulOnly.from_tortoise_orm(dept)
    print(dept_pydantic.model_dump_json(indent=4))

    # employee_count returns 0 gracefully instead of crashing
    print(f"\nemployee_count (graceful, no prefetch): {dept_pydantic.employee_count}")
    print(
        "employee_names would raise NoValuesFetched in the same scenario, "
        "but employee_count handles it and returns 0."
    )


if __name__ == "__main__":
    run_async(run())
