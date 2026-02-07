===================================
Comprehensive Migrations Project
===================================

This example demonstrates Tortoise ORM's complete migration system through a realistic ERP schema that evolves
through 14 migrations. It covers all field types, migration operations (CreateModel, AddField, AlterField, 
RemoveField, RenameField, RunPython, RunSQL, indexes, constraints), and fully reversible migrations.

Usage
=====

Apply migrations:

.. code-block:: bash

    cd examples/comprehensive_migrations_project
    uv run python -m tortoise -c config.TORTOISE_ORM migrate

Rollback migrations:

.. code-block:: bash

    uv run python -m tortoise -c config.TORTOISE_ORM downgrade erp 0001_initial_schema
    uv run python -m tortoise -c config.TORTOISE_ORM downgrade erp

Check history:

.. code-block:: bash

    uv run python -m tortoise -c config.TORTOISE_ORM history erp

Notes
=====

- All migrations are fully reversible
- Demonstrates both RunPython and RunSQL data migrations
- For SQLite, RunSQL operations use ``atomic=False`` to prevent connection deadlocks
- See ``migrations/0011_populate_computed_fields.py`` for atomic parameter usage example
