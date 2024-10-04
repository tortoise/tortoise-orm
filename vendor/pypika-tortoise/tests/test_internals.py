import unittest

from pypika import Case, Field, Table
from pypika.terms import Star


class TablesTests(unittest.TestCase):
    def test__criterion_replace_table_with_value(self):
        table = Table("a")

        c = (Field("foo") > 1).replace_table(None, table)
        self.assertEqual(c.left, table)
        self.assertEqual(c.tables_, {table})

    def test__case_tables(self):
        table = Table("a")

        c = Case().when(table.a == 1, 2 * table.a)
        self.assertIsInstance(c.tables_, set)
        self.assertSetEqual(c.tables_, {table})

    def test__star_tables(self):
        star = Star()

        self.assertEqual(star.tables_, set())

    def test__table_star_tables(self):
        table = Table("a")
        star = Star(table=table)

        self.assertEqual(star.tables_, {table})
