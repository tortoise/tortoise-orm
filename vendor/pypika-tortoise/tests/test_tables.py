# from pypika.terms import ValueWrapper, SystemTimeValue
import unittest

from pypika import SYSTEM_TIME, Database, Dialects, Query, Schema, SQLLiteQuery, Table, Tables

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"


class TableStructureTests(unittest.TestCase):
    def test_table_sql(self):
        table = Table("test_table")

        self.assertEqual('"test_table"', str(table))

    def test_table_with_alias(self):
        table = Table("test_table").as_("my_table")

        self.assertEqual('"test_table" "my_table"', table.get_sql(with_alias=True, quote_char='"'))

    def test_schema_table_attr(self):
        table = Schema("x_schema").test_table

        self.assertEqual('"x_schema"."test_table"', str(table))

    def test_table_with_schema_arg(self):
        table = Table("test_table", schema=Schema("x_schema"))

        self.assertEqual('"x_schema"."test_table"', str(table))

    def test_database_schema_table_attr(self):
        table = Database("x_db").x_schema.test_table

        self.assertEqual('"x_db"."x_schema"."test_table"', str(table))

    def test_table_with_schema_and_schema_parent_arg(self):
        table = Table("test_table", schema=Schema("x_schema", parent=Database("x_db")))

        self.assertEqual('"x_db"."x_schema"."test_table"', str(table))

    def test_table_for_system_time_sql(self):
        with self.subTest("with between criterion"):
            table = Table("test_table").for_(SYSTEM_TIME.between("2020-01-01", "2020-02-01"))

            self.assertEqual(
                "\"test_table\" FOR SYSTEM_TIME BETWEEN '2020-01-01' AND '2020-02-01'", str(table)
            )

        with self.subTest("with as of criterion"):
            table = Table("test_table").for_(SYSTEM_TIME.as_of("2020-01-01"))

            self.assertEqual("\"test_table\" FOR SYSTEM_TIME AS OF '2020-01-01'", str(table))

        with self.subTest("with from to criterion"):
            table = Table("test_table").for_(SYSTEM_TIME.from_to("2020-01-01", "2020-02-01"))

            self.assertEqual(
                "\"test_table\" FOR SYSTEM_TIME FROM '2020-01-01' TO '2020-02-01'", str(table)
            )

    def test_table_for_period_sql(self):
        with self.subTest("with between criterion"):
            table = Table("test_table")
            table = table.for_(table.valid_period.between("2020-01-01", "2020-02-01"))

            self.assertEqual(
                "\"test_table\" FOR \"valid_period\" BETWEEN '2020-01-01' AND '2020-02-01'",
                str(table),
            )

        with self.subTest("with as of criterion"):
            table = Table("test_table")
            table = table.for_(table.valid_period.as_of("2020-01-01"))

            self.assertEqual('"test_table" FOR "valid_period" AS OF \'2020-01-01\'', str(table))

        with self.subTest("with from to criterion"):
            table = Table("test_table")
            table = table.for_(table.valid_period.from_to("2020-01-01", "2020-02-01"))

            self.assertEqual(
                "\"test_table\" FOR \"valid_period\" FROM '2020-01-01' TO '2020-02-01'", str(table)
            )


class TableEqualityTests(unittest.TestCase):
    def test_tables_equal_by_name(self):
        t1 = Table("t")
        t2 = Table("t")

        self.assertEqual(t1, t2)

    def test_tables_equal_by_schema_and_name(self):
        t1 = Table("t", schema="a")
        t2 = Table("t", schema="a")

        self.assertEqual(t1, t2)

    def test_tables_equal_by_schema_and_name_using_schema(self):
        a = Schema("a")
        t1 = Table("t", schema=a)
        t2 = Table("t", schema=a)

        self.assertEqual(t1, t2)

    def test_tables_equal_by_schema_and_name_using_schema_with_parent(self):
        parent = Schema("parent")
        a = Schema("a", parent=parent)
        t1 = Table("t", schema=a)
        t2 = Table("t", schema=a)

        self.assertEqual(t1, t2)

    def test_tables_not_equal_by_schema_and_name_using_schema_with_different_parents(
        self,
    ):
        parent = Schema("parent")
        a = Schema("a", parent=parent)
        t1 = Table("t", schema=a)
        t2 = Table("t", schema=Schema("a"))

        self.assertNotEqual(t1, t2)

    def test_tables_not_equal_with_different_schemas(self):
        t1 = Table("t", schema="a")
        t2 = Table("t", schema="b")

        self.assertNotEqual(t1, t2)

    def test_tables_not_equal_with_different_names(self):
        t1 = Table("t", schema="a")
        t2 = Table("q", schema="a")

        self.assertNotEqual(t1, t2)

    def test_many_tables_with_alias(self):
        tables_data = [("table1", "t1"), ("table2", "t2"), ("table3", "t3")]
        tables = Tables(*tables_data)
        for el in tables:
            self.assertIsNotNone(el.alias)

    def test_many_tables_without_alias(self):
        tables_data = ["table1", "table2", "table3"]
        tables = Tables(*tables_data)
        for el in tables:
            self.assertIsNone(el.alias)

    def test_many_tables_with_or_not_alias(self):
        tables_data = [("table1", "t1"), ("table2"), "table3"]
        tables = Tables(*tables_data)
        for i in range(len(tables)):
            if isinstance(tables_data[i], tuple):
                self.assertIsNotNone(tables[i].alias)
            else:
                self.assertIsNone(tables[i].alias)


class TableDialectTests(unittest.TestCase):
    def test_table_with_default_query_cls(self):
        table = Table("abc")
        q = table.select("1")
        self.assertIs(q.dialect, None)

    def test_table_with_dialect_query_cls(self):
        table = Table("abc", query_cls=SQLLiteQuery)
        q = table.select("1")
        self.assertIs(q.dialect, Dialects.SQLITE)

    def test_table_factory_with_default_query_cls(self):
        table = Query.Table("abc")
        q = table.select("1")
        self.assertIs(q.dialect, None)

    def test_table_factory_with_dialect_query_cls(self):
        table = SQLLiteQuery.Table("abc")
        q = table.select("1")
        self.assertIs(q.dialect, Dialects.SQLITE)

    def test_make_tables_factory_with_default_query_cls(self):
        t1, t2 = Query.Tables("abc", "def")
        q1 = t1.select("1")
        q2 = t2.select("2")
        self.assertIs(q1.dialect, None)
        self.assertIs(q2.dialect, None)

    def test_make_tables_factory_with_dialect_query_cls(self):
        t1, t2 = SQLLiteQuery.Tables("abc", "def")
        q1 = t1.select("1")
        q2 = t2.select("2")
        self.assertIs(q1.dialect, Dialects.SQLITE)
        self.assertIs(q2.dialect, Dialects.SQLITE)

    def test_table_with_bad_query_cls(self):
        with self.assertRaises(TypeError):
            Table("abc", query_cls=object)
