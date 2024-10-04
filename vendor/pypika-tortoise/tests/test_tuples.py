import unittest

from pypika import Array, Bracket, PostgreSQLQuery, Query, Table, Tables, Tuple
from pypika.functions import Coalesce, NullIf, Sum
from pypika.terms import Field


class TupleTests(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_tuple_equality_tuple_on_both(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .where(Tuple(self.table_abc.foo, self.table_abc.bar) == Tuple(1, 2))
        )

        self.assertEqual('SELECT "foo","bar" FROM "abc" ' 'WHERE ("foo","bar")=(1,2)', str(q))

    def test_tuple_equality_tuple_on_left(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .where(Tuple(self.table_abc.foo, self.table_abc.bar) == (1, 2))
        )

        self.assertEqual('SELECT "foo","bar" FROM "abc" ' 'WHERE ("foo","bar")=(1,2)', str(q))

    def test_tuple_equality_tuple_on_right(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .where((self.table_abc.foo, self.table_abc.bar) == Tuple(1, 2))
        )

        # Order is reversed due to lack of right equals method
        self.assertEqual('SELECT "foo","bar" FROM "abc" ' 'WHERE (1,2)=("foo","bar")', str(q))

    def test_tuple_in_using_python_tuples(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .where(Tuple(self.table_abc.foo, self.table_abc.bar).isin([(1, 1), (2, 2), (3, 3)]))
        )

        self.assertEqual(
            'SELECT "foo","bar" FROM "abc" ' 'WHERE ("foo","bar") IN ((1,1),(2,2),(3,3))',
            str(q),
        )

    def test_tuple_in_using_pypika_tuples(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .where(
                Tuple(self.table_abc.foo, self.table_abc.bar).isin(
                    [Tuple(1, 1), Tuple(2, 2), Tuple(3, 3)]
                )
            )
        )

        self.assertEqual(
            'SELECT "foo","bar" FROM "abc" ' 'WHERE ("foo","bar") IN ((1,1),(2,2),(3,3))',
            str(q),
        )

    def test_tuple_in_using_mixed_tuples(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .where(
                Tuple(self.table_abc.foo, self.table_abc.bar).isin([(1, 1), Tuple(2, 2), (3, 3)])
            )
        )

        self.assertEqual(
            'SELECT "foo","bar" FROM "abc" ' 'WHERE ("foo","bar") IN ((1,1),(2,2),(3,3))',
            str(q),
        )

    def test_tuples_in_join(self):
        query = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select("*")
            .where(
                Tuple(self.table_abc.foo, self.table_efg.bar).isin([(1, 1), Tuple(2, 2), (3, 3)])
            )
        )

        self.assertEqual(
            'SELECT * FROM "abc" JOIN "efg" ON "abc"."foo"="efg"."bar" '
            'WHERE ("abc"."foo","efg"."bar") IN ((1,1),(2,2),(3,3))',
            str(query),
        )

    def test_render_alias_in_array_sql(self):
        tb = Table("tb")

        q = Query.from_(tb).select(Tuple(tb.col).as_("different_name"))
        self.assertEqual(str(q), 'SELECT ("col") "different_name" FROM "tb"')

    def test_tuple_is_aggregate(self):
        with self.subTest("None if single argument returns None for is_aggregate"):
            self.assertEqual(None, Tuple(0).is_aggregate)
            self.assertEqual(None, Tuple(Coalesce("col")).is_aggregate)

        with self.subTest("None if multiple arguments all return None for is_aggregate"):
            self.assertEqual(None, Tuple(0, "a").is_aggregate)
            self.assertEqual(None, Tuple(Coalesce("col"), NullIf("col2", 0)).is_aggregate)

        with self.subTest("True if single argument returns True for is_aggregate"):
            self.assertEqual(True, Tuple(Sum("col")).is_aggregate)

        with self.subTest("True if multiple arguments return True for is_aggregate"):
            self.assertEqual(True, Tuple(Sum("col"), Sum("col2")).is_aggregate)

        with self.subTest("True when mix of arguments returning None and True for is_aggregate"):
            self.assertEqual(
                True, Tuple(Coalesce("col"), Coalesce("col2", 0), Sum("col3")).is_aggregate
            )

        with self.subTest("False when one of the arguments returns False for is_aggregate"):
            self.assertEqual(False, Tuple(Field("col1"), Sum("col2")).is_aggregate)


class ArrayTests(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_array_general(self):
        query = Query.from_(self.table_abc).select(Array(1, "a", ["b", 2, 3]))

        self.assertEqual("SELECT [1,'a',['b',2,3]] FROM \"abc\"", str(query))

    def test_empty_psql_array(self):
        query = PostgreSQLQuery.from_(self.table_abc).select(Array())

        self.assertEqual("SELECT '{}' FROM \"abc\"", str(query))

    def test_psql_array_general(self):
        query = PostgreSQLQuery.from_(self.table_abc).select(Array(1, Array(2, 2, 2), 3))

        self.assertEqual('SELECT ARRAY[1,ARRAY[2,2,2],3] FROM "abc"', str(query))

    def test_render_alias_in_array_sql(self):
        tb = Table("tb")

        q = Query.from_(tb).select(Array(tb.col).as_("different_name"))
        self.assertEqual(str(q), 'SELECT ["col"] "different_name" FROM "tb"')


class BracketTests(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_arithmetic_with_brackets(self):
        q = Query.from_(self.table_abc).select(Bracket(self.table_abc.foo / 2) / 2)

        self.assertEqual('SELECT ("foo"/2)/2 FROM "abc"', str(q))

    def test_arithmetic_with_brackets_and_alias(self):
        q = Query.from_(self.table_abc).select(Bracket(self.table_abc.foo / 2).as_("alias"))

        self.assertEqual('SELECT ("foo"/2) "alias" FROM "abc"', str(q))
