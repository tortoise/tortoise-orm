TORTOISE_ORM = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {
        "erp": {
            "models": ["models"],
            "default_connection": "default",
            "migrations": "migrations",
        }
    },
}
