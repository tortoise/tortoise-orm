import os
from unittest import skipIf

from tortoise import Tortoise, connections, run_async
from tortoise.contrib.test import SimpleTestCase


@skipIf(os.name == "nt", "stuck with Windows")
class TestRunAsync(SimpleTestCase):
    def setUp(self):
        self.somevalue = 1

    def tearDown(self):
        run_async(self.asyncTearDown())

    async def init(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": []})
        self.somevalue = 2
        self.assertNotEqual(connections._get_storage(), {})

    async def init_raise(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": []})
        self.somevalue = 3
        self.assertNotEqual(connections._get_storage(), {})
        raise Exception("Some exception")

    def test_run_async(self):
        self.assertEqual(connections._get_storage(), {})
        self.assertEqual(self.somevalue, 1)
        run_async(self.init())
        self.assertEqual(connections._get_storage(), {})
        self.assertEqual(self.somevalue, 2)

    def test_run_async_raised(self):
        self.assertEqual(connections._get_storage(), {})
        self.assertEqual(self.somevalue, 1)
        with self.assertRaises(Exception):
            run_async(self.init_raise())
        self.assertEqual(connections._get_storage(), {})
        self.assertEqual(self.somevalue, 3)
