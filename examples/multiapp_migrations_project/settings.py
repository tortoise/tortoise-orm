TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://examples/multiapp_migrations_project/db.sqlite3",
    },
    "apps": {
        "accounts": {
            "models": ["examples.multiapp_migrations_project.accounts.models"],
            "default_connection": "default",
            "migrations": "examples.multiapp_migrations_project.accounts.migrations",
        },
        "catalog": {
            "models": ["examples.multiapp_migrations_project.catalog.models"],
            "default_connection": "default",
            "migrations": "examples.multiapp_migrations_project.catalog.migrations",
        },
        "orders": {
            "models": ["examples.multiapp_migrations_project.orders.models"],
            "default_connection": "default",
            "migrations": "examples.multiapp_migrations_project.orders.migrations",
        },
    },
}
