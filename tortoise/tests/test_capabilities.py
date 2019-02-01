from tortoise import Tortoise
from tortoise.contrib import test


class TestCapabilities(test.TestCase):
    # pylint: disable=E1101

    def setUp(self):
        self.db = Tortoise.get_connection('models')
        self.caps = self.db.capabilities

    def test_str(self):
        self.assertIn('connection', str(self.caps))

    def test_connection(self):
        self.assertIsInstance(self.caps.connection, dict)

    def test_immutability_1(self):
        self.assertIsInstance(self.caps.dialect, str)
        with self.assertRaises(AttributeError):
            self.caps.dialect = 'foo'

    @test.expectedFailure
    @test.requireCapability(connection_name='other')
    def test_connection_name(self):
        # Will fail with a `KeyError` since the connection `"other"` does not exist.
        pass

    @test.requireCapability(dialect='sqlite')
    def test_immutability_2(self):
        self.assertEquals(self.caps.connection['file'], self.db.filename)
        self.caps.connection['file'] = 'junk'
        self.assertNotEquals(self.caps.connection['file'], self.db.filename)

    @test.requireCapability(dialect='sqlite')
    @test.expectedFailure
    def test_actually_runs(self):
        self.assertTrue(False)

    def test_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.caps.bar = 'foo'

    @test.requireCapability(dialect='sqlite')
    def test_dialect_sqlite(self):
        self.assertEquals(self.caps.dialect, 'sqlite')

    @test.requireCapability(dialect='mysql')
    def test_dialect_mysql(self):
        self.assertEquals(self.caps.dialect, 'mysql')

    @test.requireCapability(dialect='postgres')
    def test_dialect_postgres(self):
        self.assertEquals(self.caps.dialect, 'postgres')
