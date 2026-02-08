# Multi-Schema Migrations Example

Demonstrates models spread across multiple PostgreSQL schemas with
cross-schema foreign keys, M2M relations, and migration autodetection.

## Schemas

| Schema      | Models                |
|-------------|-----------------------|
| `catalog`   | Category, Product     |
| `warehouse` | Supplier, Inventory   |

Cross-schema relations:
- `Product -> Category` (FK within `catalog`)
- `Inventory -> Product` (FK from `warehouse` to `catalog`)
- `Inventory -> Supplier` (FK within `warehouse`)
- `Product <-> Supplier` (M2M between `catalog` and `warehouse`)

## Prerequisites

A running PostgreSQL instance. Create the database:

```bash
createdb tortoise_schemas
```

Or adjust `settings.py` to match your connection string.

## Commands

All commands are run from the **repository root**.

### 1. Initialize migration directories

```bash
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM init
```

### 2. Generate initial migration (already generated)

```bash
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM makemigrations
```

### 3. Preview the SQL

```bash
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM sqlmigrate shop 0001_initial
```

### 4. Apply migrations to the database

```bash
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM migrate
```

### 5. Verify in psql

```sql
\dn                              -- list schemas
\dt catalog.*                    -- tables in catalog
\dt warehouse.*                  -- tables in warehouse
\d  catalog.product              -- product table details
\d  catalog.product_supplier     -- M2M through table
```

### 6. Iterate: add a field and re-migrate

Edit `models.py` (e.g. add `description = fields.TextField(null=True)` to
`Product`), then:

```bash
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM makemigrations
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM migrate
```

### 7. Downgrade

```bash
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM downgrade shop 0001_initial
```

### 8. View migration history

```bash
uv run python -m tortoise -c examples.schema_migrations_project.settings.TORTOISE_ORM history
```
