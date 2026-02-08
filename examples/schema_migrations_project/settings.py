TORTOISE_ORM = {
    "connections": {
        "default": "postgres://tortoise:qwerty123@localhost:5432/tortoise_schemas",
    },
    "apps": {
        "shop": {
            "models": ["examples.schema_migrations_project.models"],
            "default_connection": "default",
            "migrations": "examples.schema_migrations_project.migrations",
        }
    },
}
