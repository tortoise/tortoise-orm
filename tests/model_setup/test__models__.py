"""
Tests for __models__
"""

import re
from unittest.mock import AsyncMock, patch

from tortoise import Tortoise, connections
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError
from tortoise.utils import get_schema_sql


class TestGenerateSchema(test.SimpleTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        try:
            Tortoise.apps = {}
            Tortoise._inited = False
        except ConfigurationError:
            pass
        Tortoise._inited = False
        self.sqls = ""
        self.post_sqls = ""
        self.engine = test.getDBConfig(app_label="models", modules=[])["connections"]["models"][
            "engine"
        ]

    async def init_for(self, module: str, safe=False) -> None:
        if self.engine != "tortoise.backends.sqlite":
            raise test.SkipTest("sqlite only")
        with patch(
            "tortoise.backends.sqlite.client.SqliteClient.create_connection", new=AsyncMock()
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {"models": {"models": [module], "default_connection": "default"}},
                }
            )
            self.sqls = get_schema_sql(connections.get("default"), safe).split(";\n")

    def get_sql(self, text: str) -> str:
        return str(re.sub(r"[ \t\n\r]+", " ", [sql for sql in self.sqls if text in sql][0]))

    async def test_good(self):
        await self.init_for("tests.model_setup.models__models__good")
        self.assertIn("goodtournament", "; ".join(self.sqls))
        self.assertIn("inaclasstournament", "; ".join(self.sqls))
        self.assertNotIn("badtournament", "; ".join(self.sqls))

    async def test_bad(self):
        await self.init_for("tests.model_setup.models__models__bad")
        self.assertNotIn("goodtournament", "; ".join(self.sqls))
        self.assertNotIn("inaclasstournament", "; ".join(self.sqls))
        self.assertIn("badtournament", "; ".join(self.sqls))
