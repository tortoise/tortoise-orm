from tortoise import Tortoise
from tortoise.backends.base.client import Capabilities
from tortoise.contrib import test


class TestCapabilities(test.TestCase):

    def setUp(self):
        self.caps = Tortoise.get_connection('models').capabilities

    def test_str(self):
        self.assertIn('connection', str(self.caps))

    def test_kwargs(self):
        cap = Capabilities('', foo='baa')
        self.assertIn('foo', cap.__dict__)
        self.assertNotIn('baa', cap.__dict__)
        self.assertEquals(cap.foo, 'baa')  # pylint: disable=E1101

    def test_connection(self):
        self.assertIsInstance(self.caps.connection, dict)

    @test.requireCapability(dialect='sqlite')
    def test_dialect_sqlite(self):
        self.assertEquals(self.caps.dialect, 'sqlite')

    @test.requireCapability(dialect='mysql')
    def test_dialect_mysql(self):
        self.assertEquals(self.caps.dialect, 'mysql')

    @test.requireCapability(dialect='postgres')
    def test_dialect_postgres(self):
        self.assertEquals(self.caps.dialect, 'postgres')
