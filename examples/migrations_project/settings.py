TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://db.sqlite3",
    },
    "apps": {
        "blog": {
            "models": ["examples.migrations_project.models"],
            "default_connection": "default",
            "migrations": "examples.migrations_project.migrations",
        }
    },
}
