import uuid

import asynctest

from tortoise import Tortoise
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.utils import generate_schema


class TestCase(asynctest.TestCase):
    use_default_loop = True

    async def setUp(self):
        self.db = SqliteClient('/tmp/test-{}.sqlite'.format(uuid.uuid4().hex))
        await self.db.create_connection()
        Tortoise._client_routing(self.db)
        if not Tortoise._inited:
            Tortoise._init_relations()
            Tortoise._inited = True
        await generate_schema(self.db)

    async def tearDown(self):
        await self.db.close()
