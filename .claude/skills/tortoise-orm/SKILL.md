---
name: tortoise-orm
description: Tortoise ORM project conventions and development workflow. Use when working on Tortoise ORM models, fields, querysets, database backends, migrations, framework integrations, documentation, or tests in this repository.
---

# Tortoise ORM

Use this skill when changing Tortoise ORM itself, its integrations, docs, examples, or tests.

Tortoise ORM is an async-native Python ORM inspired by Django. Keep the public API explicit,
typed where practical, and predictable across SQLite, PostgreSQL, MySQL, Microsoft SQL Server,
and Oracle.

## Use uv and the Makefile

Prefer the repository's Makefile targets over ad hoc commands.

Install dependencies:

```bash
make deps
```

Run the default test suite against in-memory SQLite:

```bash
make test
```

Run the faster SQLite test target without coverage report generation:

```bash
make test_fast
```

Run style and lint checks:

```bash
make check
```

Auto-format and auto-fix lint where supported:

```bash
make style
```

Run the fuller lint pipeline (style plus mypy, bandit, and `twine check`):

```bash
make lint
```

Build the docs:

```bash
make docs
```

When running individual commands, keep using `uv run --frozen` so dependencies match `uv.lock`.

## Project layout

Core package code lives in `tortoise/`.

* `tortoise/models.py`: model metadata, model class behavior, relation setup.
* `tortoise/fields/`: field definitions and DB type mapping.
* `tortoise/queryset.py`, `tortoise/query_utils.py`, `tortoise/expressions.py`: query construction.
* `tortoise/connection.py`, `tortoise/transactions.py`, `tortoise/router.py`: connection registry, transactions, and routing.
* `tortoise/signals.py`, `tortoise/manager.py`, `tortoise/functions.py`, `tortoise/filters.py`, `tortoise/indexes.py`, `tortoise/validators.py`, `tortoise/exceptions.py`: cross-cutting features and DB primitives.
* `tortoise/backends/`: backend-specific clients, executors, schema generators, and SQL quirks.
* `tortoise/contrib/`: optional integrations such as FastAPI, Pydantic (`tortoise/contrib/pydantic/`), testing helpers, and linters.
* `tortoise/migrations/`: built-in migration framework: autodetector, executor, graph, loader, writer, recorder, operations, plus `schema_editor/`, `schema_generator/`, and `api/`.
* `tortoise/cli/`: CLI entry point and subcommand wiring (`init`, `makemigrations`, `migrate`, `upgrade`, `downgrade`, `history`, `sqlmigrate`, `heads`, `shell`).
* `tests/`: library tests and backend behavior coverage. The root `conftest.py` is the test entry point and reads `TORTOISE_TEST_DB`.
* `examples/`: runnable framework and migration examples.
* `docs/`: Sphinx documentation in reStructuredText.

## API design priorities

Follow the repository's contribution guide priorities:

* Correctness before ease of use.
* Ease of use before performance.
* Performance before maintenance cost.
* Keep behavior explicit and simple.
* Add tests for behavior changes.

Avoid surprising implicit behavior in models, querysets, migrations, and backend adapters. If a
change affects generated SQL, schema generation, relation resolution, or initialization order,
write tests that make the new contract clear.

## Async ORM conventions

Tortoise ORM public I/O APIs are async. Do not hide blocking database work inside sync helpers.

Use `async def` for functions that await database operations. Keep pure metadata and query-building
helpers sync when they do not perform I/O.

Preserve lazy query construction. QuerySet methods should generally return new or cloned querysets
until execution is explicitly awaited.

Be careful with connection and transaction context. Do not introduce global state unless it is part
of the existing connection registry or initialization lifecycle.

## Models and fields

Keep model metadata changes centralized around `MetaInfo`, model initialization, and field setup.

When changing fields:

* Preserve Python type expectations and database serialization/deserialization symmetry.
* Check backend-specific DB type mappings.
* Keep `source_field`, `model_field_name`, and relation metadata consistent.
* Add tests for validation, schema generation, query filters, and serialization when relevant.

When changing table, schema, or relation behavior, cover inheritance and abstract-model cases. Also
check generated table names, through tables, indexes, constraints, and backward-compatible defaults.

## Query and expression behavior

When changing queries, verify both the Python-facing API and generated SQL.

Prefer existing abstractions in `query_utils`, `expressions`, `functions`, and backend executors
instead of hand-building SQL strings in high-level code.

Add tests for:

* Filtering and excluding.
* Related-field traversal.
* Ordering and distinct behavior.
* Aggregates, functions, and annotations.
* Empty inputs and null handling.
* Backend-specific SQL differences when applicable.

## Database backends

Keep backend-specific behavior inside the backend packages unless the contract truly belongs in
shared code.

Run targeted tests with the matching Makefile target when a change touches a backend:

```bash
make test_postgres_asyncpg
make test_postgres_psycopg
make test_mysql
make test_mysql_asyncmy
make test_mssql
make test_oracle
```

Use environment variables from the Makefile for database passwords and drivers. SQLite tests should
remain the first local verification path for most changes.

## Migrations

For migration framework or CLI changes, update tests and examples that exercise:

* `tortoise init`
* `tortoise makemigrations`
* `tortoise migrate` (and its alias `tortoise upgrade`)
* `tortoise downgrade`
* `tortoise history`
* `tortoise sqlmigrate`
* `tortoise heads`

Migration examples to consult and keep aligned with framework changes:

* `examples/migrations_project/`: minimal single-app migrations.
* `examples/multiapp_migrations_project/`: cross-app dependencies.
* `examples/schema_migrations_project/`: schema-focused migrations.
* `examples/comprehensive_migrations_project/`: end-to-end coverage; CI exercises this one.

Migration changes should preserve deterministic output so generated files are stable across
repeated runs.

## Pydantic and framework integrations

For Pydantic changes, remember that this project targets Pydantic v2. The integration code lives
in `tortoise/contrib/pydantic/`. Keep generated schemas, computed fields, relation prefetching,
and serialization behavior explicit.

For FastAPI, Starlette, Sanic, BlackSheep, aiohttp, or Quart integration changes, keep examples and
docs aligned with implementation. The CI runs the FastAPI, BlackSheep, and Sanic example tests from
`.github/workflows/ci.yml`; use those examples as executable documentation.

FastAPI example checks (mirroring CI):

```bash
PYTHONPATH=examples/fastapi uv run --frozen tortoise -c config.TORTOISE_ORM migrate
PYTHONPATH=examples/fastapi uv run --frozen pytest -n auto --cov=tortoise --cov-append --cov-branch --tb=native -q examples/fastapi/_tests.py
```

## Testing guidance

Use the smallest meaningful test first, then broaden when behavior crosses module boundaries. The
root `conftest.py` is the test entry point and reads the `TORTOISE_TEST_DB` environment variable
to pick the backend, so set it explicitly for targeted runs.

For local changes, prefer targeted pytest runs:

```bash
TORTOISE_TEST_DB=sqlite://:memory: uv run --frozen pytest tests/test_file.py::test_name -q
```

Then run an appropriate Makefile target. For broad ORM behavior changes, run at least SQLite tests
and mention any database-specific test targets that could not be run locally.

On Windows, the contribution guide notes that running the full suite natively is not supported yet;
WSL is the recommended path for full test runs.

## Documentation

Update docs when changing public APIs, integration behavior, migrations, or examples.

Docs are Sphinx/reStructuredText. Keep examples importable and consistent with files under
`examples/`. If docs include literal examples from files, update the source file rather than
duplicating stale snippets.

Build docs with:

```bash
make docs
```

## Style

Follow `pyproject.toml`:

* Python `>=3.10`.
* Ruff line length 100.
* Use future annotations where the existing file does.
* Keep imports sorted by Ruff.
* Prefer type annotations for public APIs and complex internal helpers.

Use comments sparingly. Add them only when they explain non-obvious ORM, SQL, migration, or
backend behavior.

## Compatibility

Treat public model, field, queryset, connection, migration, and contrib APIs as compatibility
sensitive. When changing behavior, check existing docs and tests for implied guarantees.

Do not remove deprecations or change defaults casually. If a change introduces a new option, make
the default preserve existing behavior unless the task explicitly calls for a breaking change.

## Do not do this

Do not hand-roll SQL in high-level APIs when backend abstractions already exist.

Do not make async APIs perform blocking work.

Do not add broad abstractions without tests that show the shared behavior.

Do not update generated lock files, formatting, docs, or unrelated modules unless the task requires
it.

Do not assume a single database backend. If behavior differs by backend, make the contract explicit
and test the difference.
