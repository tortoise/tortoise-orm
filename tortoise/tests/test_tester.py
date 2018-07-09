from tortoise.contrib import test


class TestTesterSync(test.TestCase):

    def setUp(self):
        self.moo = 'SET'

    def tearDown(self):
        self.assertEqual(self.moo, 'SET')

    @test.skip
    def test_skip(self):
        self.assertTrue(False)

    @test.expectedFailure
    def test_fail(self):
        self.assertTrue(False)

    def test_moo(self):
        self.assertEqual(self.moo, 'SET')


class TestTesterASync(test.TestCase):

    async def setUp(self):
        self.baa = 'TES'

    async def tearDown(self):
        self.assertEqual(self.baa, 'TES')

    @test.skip
    async def test_skip(self):
        self.assertTrue(False)

    @test.expectedFailure
    async def test_fail(self):
        self.assertTrue(False)

    async def test_moo(self):
        self.assertEqual(self.baa, 'TES')
