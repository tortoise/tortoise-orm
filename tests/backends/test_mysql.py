"""
Test some mysql-specific features
"""

import ssl

from tortoise import Tortoise
from tortoise.contrib import test


class TestMySQL(test.SimpleTestCase):
    async def asyncSetUp(self):
        if Tortoise._inited:
            await self._tearDownDB()
        self.db_config = test.getDBConfig(app_label="models", modules=["tests.testmodels"])
        if self.db_config["connections"]["models"]["engine"] != "tortoise.backends.mysql":
            raise test.SkipTest("MySQL only")

    async def asyncTearDown(self) -> None:
        if Tortoise._inited:
            await Tortoise._drop_databases()
        await super().asyncTearDown()

    async def test_bad_charset(self):
        self.db_config["connections"]["models"]["credentials"]["charset"] = "terrible"
        with self.assertRaisesRegex(ConnectionError, "Unknown charset"):
            await Tortoise.init(self.db_config, _create_db=True)

    async def test_ssl_true(self):
        self.db_config["connections"]["models"]["credentials"]["ssl"] = True
        try:
            import asyncmy  # noqa pylint: disable=unused-import

            # setting read_timeout for asyncmy. Otherwise, it will hang forever.
            self.db_config["connections"]["models"]["credentials"]["read_timeout"] = 1
        except ImportError:
            pass

        with self.assertRaises(ConnectionError):
            await Tortoise.init(self.db_config, _create_db=True)

    async def test_ssl_custom(self):
        # Expect connectionerror or pass
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.db_config["connections"]["models"]["credentials"]["ssl"] = ctx
        try:
            await Tortoise.init(self.db_config, _create_db=True)
        except ConnectionError:
            pass
