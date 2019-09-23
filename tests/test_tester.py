# pylint: disable=W1503
from tortoise.contrib import test


class TestTesterSync(test.SimpleTestCase):
    def setUp(self):
        self.moo = "SET"

    def tearDown(self):
        self.assertEqual(self.moo, "SET")

    @test.skip("Skip it")
    def test_skip(self):
        self.assertTrue(False)

    @test.expectedFailure
    def test_fail(self):
        self.assertTrue(False)

    def test_moo(self):
        self.assertEqual(self.moo, "SET")


class TestTesterASync(test.SimpleTestCase):
    async def setUp(self):
        self.baa = "TES"

    async def tearDown(self):
        self.assertEqual(self.baa, "TES")

    @test.skip("Skip it")
    async def test_skip(self):
        self.assertTrue(False)

    @test.expectedFailure
    async def test_fail(self):
        self.assertTrue(False)

    async def test_moo(self):
        self.assertEqual(self.baa, "TES")
