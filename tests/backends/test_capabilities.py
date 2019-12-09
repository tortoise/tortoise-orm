from tortoise import Tortoise
from tortoise.contrib import test


class TestCapabilities(test.TestCase):
    # pylint: disable=E1101

    def setUp(self):
        self.db = Tortoise.get_connection("models")
        self.caps = self.db.capabilities

    def test_str(self):
        self.assertIn("requires_limit", str(self.caps))

    def test_immutability_1(self):
        self.assertIsInstance(self.caps.dialect, str)
        with self.assertRaises(AttributeError):
            self.caps.dialect = "foo"

    @test.expectedFailure
    @test.requireCapability(connection_name="other")
    def test_connection_name(self):
        # Will fail with a `KeyError` since the connection `"other"` does not exist.
        pass

    @test.requireCapability(dialect="sqlite")
    @test.expectedFailure
    def test_actually_runs(self):
        self.assertTrue(False)  # pylint: disable=W1503

    def test_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.caps.bar = "foo"

    @test.requireCapability(dialect="sqlite")
    def test_dialect_sqlite(self):
        self.assertEqual(self.caps.dialect, "sqlite")

    @test.requireCapability(dialect="mysql")
    def test_dialect_mysql(self):
        self.assertEqual(self.caps.dialect, "mysql")

    @test.requireCapability(dialect="postgres")
    def test_dialect_postgres(self):
        self.assertEqual(self.caps.dialect, "postgres")
