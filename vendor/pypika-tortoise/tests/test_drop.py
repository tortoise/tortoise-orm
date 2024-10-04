import unittest

from pypika import Columns, Query, Tables


class DropTableTests(unittest.TestCase):
    new_table, existing_table = Tables("abc", "efg")
    foo, bar = Columns(("a", "INT"), ("b", "VARCHAR(100)"))

    def test_drop_table(self):
        q = Query.drop_table(self.new_table)

        self.assertEqual('DROP TABLE "abc"', str(q))

    def test_drop_table_if_exists(self):
        q = Query.drop_table(self.new_table).if_exists()

        self.assertEqual('DROP TABLE IF EXISTS "abc"', str(q))
