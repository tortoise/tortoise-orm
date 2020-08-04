import os
from unittest import TestCase, skipIf

from tortoise import Tortoise, run_async


@skipIf(os.name == "nt", "stuck with Windows")
class TestRunAsync(TestCase):
    def setUp(self):
        self.somevalue = 1

    async def init(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": []})
        self.somevalue = 2
        self.assertNotEqual(Tortoise._connections, {})

    async def init_raise(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": []})
        self.somevalue = 3
        self.assertNotEqual(Tortoise._connections, {})
        raise Exception("Some exception")

    def test_run_async(self):
        self.assertEqual(Tortoise._connections, {})
        self.assertEqual(self.somevalue, 1)
        run_async(self.init())
        self.assertEqual(Tortoise._connections, {})
        self.assertEqual(self.somevalue, 2)

    def test_run_async_raised(self):
        self.assertEqual(Tortoise._connections, {})
        self.assertEqual(self.somevalue, 1)
        with self.assertRaises(Exception):
            run_async(self.init_raise())
        self.assertEqual(Tortoise._connections, {})
        self.assertEqual(self.somevalue, 3)
