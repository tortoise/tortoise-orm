"""
Test configuration for Dameng database
"""

import os

# Dameng test database configuration
DAMENG_TEST_DB = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.dameng",
            "credentials": {
                "host": os.getenv("DAMENG_HOST", "127.0.0.1"),
                "port": int(os.getenv("DAMENG_PORT", "5236")),
                "user": os.getenv("DAMENG_USER", "SYSDBA"),
                "password": os.getenv("DAMENG_PASSWORD", "SYSDBA"),
                "database": os.getenv("DAMENG_DATABASE", "DAMENG"),
                "minsize": 1,
                "maxsize": 5,
                "charset": "utf8",
            }
        }
    },
    "apps": {
        "models": {
            "models": ["tests.testmodels"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "UTC",
}

# Test database URL
DAMENG_TEST_URL = "dm://SYSDBA:SYSDBA@127.0.0.1:5236/DAMENG"