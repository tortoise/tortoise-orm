import unittest

from pypika import (
    SYSTEM_TIME,
    Field,
    Interval,
    JoinException,
    JoinType,
    MySQLQuery,
    Query,
    SetOperationException,
    Table,
    Tables,
)
from pypika import functions as fn

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"


class SelectQueryJoinTests(unittest.TestCase):
    table0, table1, hij = Tables("abc", "efg", "hij")

    def test_default_join_type(self):
        query = (
            Query.from_(self.table0)
            .join(self.table1)
            .on(self.table0.foo == self.table1.bar)
            .select("*")
        )

        self.assertEqual('SELECT * FROM "abc" JOIN "efg" ON "abc"."foo"="efg"."bar"', str(query))

    def test_inner_join(self):
        expected = 'SELECT * FROM "abc" JOIN "efg" ON "abc"."foo"="efg"."bar"'

        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.inner)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )
            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .inner_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )
            self.assertEqual(expected, str(query))

    def test_left_join(self):
        expected = 'SELECT * FROM "abc" LEFT JOIN "efg" ON "abc"."foo"="efg"."bar"'

        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.left)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .left_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )
            self.assertEqual(expected, str(query))

    def test_right_join(self):
        expected = 'SELECT * FROM "abc" RIGHT JOIN "efg" ON "abc"."foo"="efg"."bar"'

        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.right)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .right_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )
            self.assertEqual(expected, str(query))

    def test_hash_join(self):
        expected = 'SELECT * FROM "abc" HASH JOIN "efg" ON "abc"."foo"="efg"."bar"'

        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.hash)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .hash_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )
            self.assertEqual(expected, str(query))

    def test_outer_join(self):
        expected = 'SELECT * FROM "abc" FULL OUTER JOIN "efg" ON "abc"."foo"="efg"."bar"'

        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.outer)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .outer_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )
            self.assertEqual(expected, str(query))

    def test_cross_join(self):
        expected = 'SELECT * FROM "abc" CROSS JOIN "efg" ON "abc"."foo"="efg"."bar"'

        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.cross)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .cross_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )
            self.assertEqual(expected, str(query))

    def test_left_outer_join(self):
        expected = 'SELECT * FROM "abc" LEFT OUTER JOIN "efg" ON "abc"."foo"="efg"."bar"'
        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.left_outer)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .left_outer_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

    def test_right_outer_join(self):
        expected = 'SELECT * FROM "abc" RIGHT OUTER JOIN "efg" ON "abc"."foo"="efg"."bar"'
        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.right_outer)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .right_outer_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

    def test_full_outer_join(self):
        expected = 'SELECT * FROM "abc" FULL OUTER JOIN "efg" ON "abc"."foo"="efg"."bar"'

        with self.subTest("join with enum"):
            query = (
                Query.from_(self.table0)
                .join(self.table1, how=JoinType.full_outer)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

        with self.subTest("join function"):
            query = (
                Query.from_(self.table0)
                .full_outer_join(self.table1)
                .on(self.table0.foo == self.table1.bar)
                .select("*")
            )

            self.assertEqual(expected, str(query))

    def test_join_on_field_single(self):
        query = Query.from_(self.table0).join(self.table1).on_field("foo").select("*")
        self.assertEqual('SELECT * FROM "abc" JOIN "efg" ON "abc"."foo"="efg"."foo"', str(query))

    def test_join_on_field_multi(self):
        query = Query.from_(self.table0).join(self.table1).on_field("foo", "bar").select("*")
        self.assertEqual(
            'SELECT * FROM "abc" JOIN "efg" ON "abc"."foo"="efg"."foo" '
            'AND "abc"."bar"="efg"."bar"',
            str(query),
        )

    def test_join_on_field_multi_with_extra_join(self):
        query = (
            Query.from_(self.table0)
            .join(self.hij)
            .on_field("buzz")
            .join(self.table1)
            .on_field("foo", "bar")
            .select("*")
        )

        self.assertEqual(
            'SELECT * FROM "abc" JOIN "hij" ON "abc"."buzz"="hij"."buzz" '
            'JOIN "efg" ON "abc"."foo"="efg"."foo" AND "abc"."bar"="efg"."bar"',
            str(query),
        )

    def test_join_using_string_field_name(self):
        query = Query.from_(self.table0).join(self.table1).using("id").select("*")

        self.assertEqual('SELECT * FROM "abc" JOIN "efg" USING ("id")', str(query))

    def test_join_using_multiple_fields(self):
        query = Query.from_(self.table0).join(self.table1).using("foo", "bar").select("*")

        self.assertEqual('SELECT * FROM "abc" JOIN "efg" USING ("foo","bar")', str(query))

    def test_join_using_with_quote_char(self):
        query = Query.from_(self.table0).join(self.table1).using("foo", "bar").select("*")

        self.assertEqual("SELECT * FROM abc JOIN efg USING (foo,bar)", query.get_sql(quote_char=""))

    def test_join_using_without_fields_raises_exception(self):
        with self.assertRaises(JoinException):
            Query.from_(self.table0).join(self.table1).using()

    def test_join_on_field_without_fields_raises_exception(self):
        with self.assertRaises(JoinException):
            Query.from_(self.table0).join(self.table1).on_field()

    def test_join_arithmetic_field(self):
        q = (
            Query.from_(self.table0)
            .join(self.table1)
            .on(self.table0.dt == (self.table1.dt - Interval(weeks=1)))
            .select("*")
        )

        self.assertEqual(
            'SELECT * FROM "abc" ' 'JOIN "efg" ON "abc"."dt"="efg"."dt"-INTERVAL \'1 WEEK\'',
            str(q),
        )

    def test_join_with_arithmetic_function_in_select(self):
        q = (
            Query.from_(
                self.table0,
            )
            .join(self.table1)
            .on(self.table0.dt == (self.table1.dt - Interval(weeks=1)))
            .select(self.table0.fiz - self.table0.buz, self.table1.star)
        )

        self.assertEqual(
            'SELECT "abc"."fiz"-"abc"."buz","efg".* FROM "abc" '
            'JOIN "efg" ON "abc"."dt"="efg"."dt"-INTERVAL \'1 WEEK\'',
            str(q),
        )

    def test_join_on_complex_criteria(self):
        q = (
            Query.from_(self.table0)
            .join(self.table1, how=JoinType.right)
            .on((self.table0.foo == self.table1.fiz) & (self.table0.bar == self.table1.buz))
            .select("*")
        )

        self.assertEqual(
            'SELECT * FROM "abc" '
            'RIGHT JOIN "efg" ON "abc"."foo"="efg"."fiz" AND "abc"."bar"="efg"."buz"',
            str(q),
        )

    def test_join_on_subquery_criteria(self):
        table_a, table_b, table_c = Tables("a", "b", "c")
        subquery = Query.from_(table_c).select("id").limit(1)
        query = (
            Query.from_(table_a)
            .select("*")
            .join(table_b)
            .on((table_a.b_id == table_b.id) & (table_b.c_id == subquery))
        )

        self.assertEqual(
            "SELECT * "
            'FROM "a" '
            'JOIN "b" ON "a"."b_id"="b"."id" AND "b"."c_id"='
            '(SELECT "id" FROM "c" LIMIT 1)',
            str(query),
        )

    def test_use_different_table_objects_for_same_table(self):
        table = Table("t")
        q = Query.from_(table).select("*").where(Field("id", table=table) == 1)

        self.assertEqual('SELECT * FROM "t" WHERE "id"=1', str(q))

    def test_join_second_table_in_from_clause(self):
        table_a, table_b, table_c = Tables("a", "b", "c")
        q = (
            Query.from_(table_a)
            .from_(table_b)
            .select("*")
            .join(table_c)
            .on(table_b.c_id == table_c.id)
        )

        self.assertEqual("SELECT * " 'FROM "a","b" ' 'JOIN "c" ON "b"."c_id"="c"."id"', str(q))

    def test_cross_join_on_table(self):
        table_a, table_b = Tables("a", "b")
        q = Query.from_(table_a).join(table_b).cross().select("*")

        self.assertEqual('SELECT * FROM "a" CROSS JOIN "b"', str(q))

    def test_cross_join_on_subquery(self):
        table_a, table_b = Tables("a", "b")
        q_a = Query.from_(table_a).select("*")
        q_b = Query.from_(table_b).select("*").join(q_a).cross().select("*")

        self.assertEqual('SELECT * FROM "b" CROSS JOIN (SELECT * FROM "a") "sq0"', str(q_b))

    def test_join_on_collate(self):
        table_a, table_b = Tables("a", "b")

        q1 = (
            Query.from_(table_a)
            .select(table_b.ouch)
            .join(table_b)
            .on(table_a.foo == table_b.boo, collate="utf8_general_ci")
        )
        q2 = Query.from_(table_a).select(table_b.ouch).join(table_b).on(table_a.foo == table_b.boo)

        self.assertEqual(
            'SELECT "b"."ouch" FROM "a" JOIN "b" ON "a"."foo"="b"."boo" COLLATE utf8_general_ci',
            str(q1),
        )
        self.assertEqual('SELECT "b"."ouch" FROM "a" JOIN "b" ON "a"."foo"="b"."boo"', str(q2))

    def test_temporal_join(self):
        t0 = self.table0.for_(SYSTEM_TIME.as_of("2020-01-01"))
        t1 = self.table1.for_(SYSTEM_TIME.as_of("2020-01-01"))
        query = Query.from_(t0).join(t1).on(t0.foo == t1.bar).select("*")

        self.assertEqual(
            "SELECT * FROM \"abc\" FOR SYSTEM_TIME AS OF '2020-01-01' "
            "JOIN \"efg\" FOR SYSTEM_TIME AS OF '2020-01-01' "
            'ON "abc"."foo"="efg"."bar"',
            str(query),
        )


class JoinBehaviorTests(unittest.TestCase):
    table_abc, table_efg, table_hij, table_klm = Tables("abc", "efg", "hij", "klm")

    def test_select__ordered_select_clauses(self):
        q = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select(
                self.table_abc.baz,
                self.table_efg.buz,
                self.table_abc.fiz,
                self.table_efg.bam,
            )
        )

        self.assertEqual(
            'SELECT "abc"."baz","efg"."buz","abc"."fiz","efg"."bam" FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."bar"',
            str(q),
        )

    def test_select__star_for_table(self):
        q = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .join(self.table_hij)
            .on(self.table_abc.buz == self.table_hij.bam)
            .select(self.table_abc.star)
            .select(self.table_efg.star)
            .select(self.table_hij.star)
        )

        self.assertEqual(
            'SELECT "abc".*,"efg".*,"hij".* FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."bar" '
            'JOIN "hij" ON "abc"."buz"="hij"."bam"',
            str(q),
        )

    def test_select__star_for_table__replacement(self):
        q = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .join(self.table_hij)
            .on(self.table_abc.buz == self.table_hij.bam)
            .select(self.table_abc.foo, self.table_efg.bar, self.table_hij.bam)
            .select(self.table_abc.star, self.table_efg.star, self.table_hij.star)
        )

        self.assertEqual(
            'SELECT "abc".*,"efg".*,"hij".* FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."bar" '
            'JOIN "hij" ON "abc"."buz"="hij"."bam"',
            str(q),
        )

    def test_select_fields_with_where(self):
        q = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .join(self.table_hij)
            .on(self.table_abc.buz == self.table_hij.bam)
            .select(self.table_abc.foo, self.table_efg.bar, self.table_hij.bam)
            .where(self.table_abc.foo > 1)
            .where(self.table_efg.bar != 2)
        )

        self.assertEqual(
            'SELECT "abc"."foo","efg"."bar","hij"."bam" FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."bar" '
            'JOIN "hij" ON "abc"."buz"="hij"."bam" '
            'WHERE "abc"."foo">1 AND "efg"."bar"<>2',
            str(q),
        )

    def test_require_condition(self):
        with self.assertRaises(JoinException):
            Query.from_(self.table_abc).join(self.table_efg).on(None)

    def test_require_condition_with_both_tables(self):
        with self.assertRaises(JoinException):
            Query.from_(self.table_abc).join(self.table_efg).on(
                self.table_abc.foo == self.table_hij.bar
            )

        with self.assertRaises(JoinException):
            Query.from_(self.table_abc).join(self.table_efg).on(
                self.table_hij.foo == self.table_efg.bar
            )

        with self.assertRaises(JoinException):
            Query.from_(self.table_abc).join(self.table_efg).on(
                self.table_hij.foo == self.table_klm.bar
            )

    def test_join_same_table(self):
        table1 = Table("abc")
        table2 = Table("abc")
        q = (
            Query.from_(table1)
            .join(table2)
            .on(table1.foo == table2.bar)
            .select(table1.foo, table2.buz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","abc2"."buz" FROM "abc" '
            'JOIN "abc" "abc2" ON "abc"."foo"="abc2"."bar"',
            str(q),
        )

    def test_join_same_table_with_prefixes(self):
        table1 = Table("abc").as_("x")
        table2 = Table("abc").as_("y")
        q = (
            Query.from_(table1)
            .join(table2)
            .on(table1.foo == table2.bar)
            .select(table1.foo, table2.buz)
        )

        self.assertEqual(
            'SELECT "x"."foo","y"."buz" FROM "abc" "x" ' 'JOIN "abc" "y" ON "x"."foo"="y"."bar"',
            str(q),
        )

    def test_join_table_twice(self):
        table1, table2 = Table("efg").as_("efg1"), Table("efg").as_("efg2")
        q = (
            Query.from_(self.table_abc)
            .join(table1)
            .on(self.table_abc.foo == table1.bar)
            .join(table2)
            .on(self.table_abc.foo == table2.bam)
            .select(self.table_abc.foo, table1.fiz, table2.buz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","efg1"."fiz","efg2"."buz" FROM "abc" '
            'JOIN "efg" "efg1" ON "abc"."foo"="efg1"."bar" '
            'JOIN "efg" "efg2" ON "abc"."foo"="efg2"."bam"',
            str(q),
        )

    def test_select__fields_after_table_star(self):
        q = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select(self.table_abc.star, self.table_efg.bar)
            .select(self.table_abc.foo)
        )

        self.assertEqual(
            'SELECT "abc".*,"efg"."bar" FROM "abc" JOIN "efg" ON "abc"."foo"="efg"."bar"',
            str(q),
        )

    def test_fail_when_joining_unknown_type(self):
        with self.assertRaises(ValueError):
            Query.from_(self.table_abc).join("this is a string")

    def test_immutable__tables(self):
        query1 = Query.from_(self.table_abc).select(self.table_abc.foo)
        query2 = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select(self.table_abc.foo, self.table_efg.buz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","efg"."buz" FROM "abc" ' 'JOIN "efg" ON "abc"."foo"="efg"."bar"',
            str(query2),
        )
        self.assertEqual('SELECT "foo" FROM "abc"', str(query1))

    def test_select_field_from_missing_table(self):
        """
        Previously we validated the select field was a member of a table
        in the query (e.g. FROM clause or a JOIN). However this made
        correlated subqueries awkward to write (subqueries which refer
        to their parent table. So the validation was removed.

        None of the following raise an error. Previously raised JoinException
        """
        Query.from_(self.table_abc).select(self.table_efg.foo)

        Query.from_(self.table_abc).where(self.table_efg.foo == 0)

        Query.from_(self.table_abc).where(fn.Sum(self.table_efg.foo) == 0)

        Query.from_(self.table_abc).select(
            fn.Sum(self.table_abc.bar * 2) + fn.Sum(self.table_efg.foo * 2)
        )

        Query.from_(self.table_abc).groupby(self.table_efg.foo)

        Query.from_(self.table_abc).groupby(self.table_abc.foo).having(self.table_efg.bar)

        subquery = (
            Query.from_(self.table_efg)
            .select(self.table_efg.id)
            .where(self.table_efg.abc_id == self.table_abc.id)
        )
        query = Query.from_(self.table_abc).select(subquery.as_("efg_id").limit(1))
        self.assertEqual(
            'SELECT (SELECT "efg"."id" FROM "efg" WHERE "efg"."abc_id"="abc"."id" LIMIT 1) "efg_id" FROM "abc"',
            str(query),
        )

    def test_ignore_table_references(self):
        query = Query.from_(Table("abc")).select(Table("abc").foo)

        self.assertEqual('SELECT "foo" FROM "abc"', str(query))

    def test_prefixes_added_to_groupby(self):
        test_query = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select(self.table_abc.foo, fn.Sum(self.table_efg.buz))
            .groupby(self.table_abc.foo)
        )

        self.assertEqual(
            'SELECT "abc"."foo",SUM("efg"."buz") FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."bar" '
            'GROUP BY "abc"."foo"',
            str(test_query),
        )

    def test_prefixes_added_to_orderby(self):
        test_query = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select(self.table_abc.foo, self.table_efg.buz)
            .orderby(self.table_abc.foo)
        )

        self.assertEqual(
            'SELECT "abc"."foo","efg"."buz" FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."bar" '
            'ORDER BY "abc"."foo"',
            str(test_query),
        )

    def test_prefixes_added_to_function_in_orderby(self):
        test_query = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select(self.table_abc.foo, self.table_efg.buz)
            .orderby(fn.Date(self.table_abc.foo))
        )

        self.assertEqual(
            'SELECT "abc"."foo","efg"."buz" FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."bar" '
            'ORDER BY DATE("abc"."foo")',
            str(test_query),
        )

    def test_join_from_join(self):
        test_query = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.efg_id == self.table_efg.id)
            .join(self.table_hij)
            .on(self.table_efg.hij_id == self.table_hij.id)
            .select(self.table_abc.foo, self.table_efg.bar, self.table_hij.fizz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","efg"."bar","hij"."fizz" FROM "abc" '
            'JOIN "efg" ON "abc"."efg_id"="efg"."id" '
            'JOIN "hij" ON "efg"."hij_id"="hij"."id"',
            str(test_query),
        )

    def test_join_query_without_alias(self):
        subquery = Query.from_(self.table_efg).select(
            self.table_efg.base_id.as_("x"), self.table_efg.fizz, self.table_efg.buzz
        )

        test_query = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(subquery.x == self.table_abc.id)
            .select(self.table_abc.foo, subquery.fizz, subquery.buzz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","sq0"."fizz","sq0"."buzz" '
            'FROM "abc" JOIN ('
            'SELECT "base_id" "x","fizz","buzz" FROM "efg"'
            ') "sq0" '
            'ON "sq0"."x"="abc"."id"',
            str(test_query),
        )

    def test_join_query_with_column_alias(self):
        subquery = (
            Query.from_(self.table_efg)
            .select(
                self.table_efg.base_id.as_("x"),
                self.table_efg.fizz,
                self.table_efg.buzz,
            )
            .as_("subq")
        )

        test_query = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(subquery.x == self.table_abc.id)
            .select(self.table_abc.foo, subquery.fizz, subquery.buzz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","subq"."fizz","subq"."buzz" '
            'FROM "abc" JOIN ('
            'SELECT "base_id" "x","fizz","buzz" FROM "efg"'
            ') "subq" '
            'ON "subq"."x"="abc"."id"',
            str(test_query),
        )

    def test_join_query_with_table_alias(self):
        xxx = self.table_efg.as_("xxx")
        subquery = Query.from_(xxx).select(xxx.base_id, xxx.fizz, xxx.buzz).as_("subq")

        test_query = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(subquery.x == self.table_abc.id)
            .select(self.table_abc.foo, subquery.fizz, subquery.buzz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","subq"."fizz","subq"."buzz" '
            'FROM "abc" JOIN ('
            'SELECT "xxx"."base_id","xxx"."fizz","xxx"."buzz" FROM "efg" "xxx"'
            ') "subq" '
            'ON "subq"."x"="abc"."id"',
            str(test_query),
        )

    def test_join_query_with_setoperation(self):
        subquery = (
            Query.from_(self.table_abc)
            .select("*")
            .union(Query.from_(self.table_abc).select("*"))
            .as_("subq")
        )

        test_query = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(subquery.x == self.table_abc.id)
            .select(self.table_abc.foo)
        )

        self.assertEqual(
            'SELECT "abc"."foo" FROM "abc" '
            "JOIN "
            '((SELECT * FROM "abc") '
            "UNION "
            '(SELECT * FROM "abc")) "subq" '
            'ON "subq"."x"="abc"."id"',
            str(test_query),
        )


class UnionTests(unittest.TestCase):
    table1, table2 = Tables("abc", "efg")

    def test_union(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION (SELECT "bar" FROM "efg")',
            str(query1 + query2),
        )
        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION (SELECT "bar" FROM "efg")',
            str(query1.union(query2)),
        )

    def test_union_multiple(self):
        table3, table4 = Tables("hij", "lmn")
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)
        query3 = Query.from_(table3).select(table3.baz)
        query4 = Query.from_(table4).select(table4.faz)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION '
            '(SELECT "bar" FROM "efg") UNION '
            '(SELECT "baz" FROM "hij") UNION '
            '(SELECT "faz" FROM "lmn")',
            str(query1 + query2 + query3 + query4),
        )
        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION '
            '(SELECT "bar" FROM "efg") UNION '
            '(SELECT "baz" FROM "hij") UNION '
            '(SELECT "faz" FROM "lmn")',
            str(query1.union(query2).union(query3).union(query4)),
        )

    def test_union_all(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION ALL (SELECT "bar" FROM "efg")',
            str(query1 * query2),
        )
        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION ALL (SELECT "bar" FROM "efg")',
            str(query1.union_all(query2)),
        )

    def test_union_all_multiple(self):
        table3, table4 = Tables("hij", "lmn")
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)
        query3 = Query.from_(table3).select(table3.baz)
        query4 = Query.from_(table4).select(table4.faz)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION ALL '
            '(SELECT "bar" FROM "efg") UNION ALL '
            '(SELECT "baz" FROM "hij") UNION ALL '
            '(SELECT "faz" FROM "lmn")',
            str(query1 * query2 * query3 * query4),
        )
        self.assertEqual(
            '(SELECT "foo" FROM "abc") UNION ALL '
            '(SELECT "bar" FROM "efg") UNION ALL '
            '(SELECT "baz" FROM "hij") UNION ALL '
            '(SELECT "faz" FROM "lmn")',
            str(query1.union_all(query2).union_all(query3).union_all(query4)),
        )

    def test_union_with_order_by(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        union_query = str((query1 + query2).orderby(query1.field("a")))
        union_all_query = str((query1 * query2).orderby(query1.field("a")))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "UNION "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "a"',
            union_query,
        )

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "UNION ALL "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "a"',
            union_all_query,
        )

    def test_union_with_order_by_use_union_query_field(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        union_query = query1 + query2
        union_query = str(union_query.orderby(union_query.field("a")))
        union_all_query = query1 * query2
        union_all_query = str(union_all_query.orderby(union_all_query.field("a")))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "UNION "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "a"',
            union_query,
        )
        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "UNION ALL "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "a"',
            union_all_query,
        )

    def test_union_with_order_by_with_aliases(self):
        query1 = Query.from_(self.table1.as_("a")).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2.as_("b")).select(self.table2.bar.as_("a"))

        union_all_query = str((query1 * query2).orderby(query1.field("a")))
        union_query = str((query1 + query2).orderby(query1.field("a")))
        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc" "a")'
            " UNION ALL "
            '(SELECT "bar" "a" FROM "efg" "b")'
            ' ORDER BY "a"',
            union_all_query,
        )
        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc" "a")'
            " UNION "
            '(SELECT "bar" "a" FROM "efg" "b")'
            ' ORDER BY "a"',
            union_query,
        )

    def test_union_with_order_by_use_union_query_field_with_aliases(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        union_query = (query1 + query2).as_("x")
        union_query = union_query.orderby(union_query.field("a"))
        union_all_query = (query1 * query2).as_("x")
        union_all_query = union_all_query.orderby(union_all_query.field("a"))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "UNION "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "x"."a"',
            str(union_query),
        )
        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "UNION ALL "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "x"."a"',
            str(union_all_query),
        )

    def test_require_equal_number_of_fields(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.fiz, self.table2.buz)

        with self.assertRaises(SetOperationException):
            str(query1 + query2)

    def test_mysql_query_does_not_wrap_unioned_queries_with_params(self):
        query1 = MySQLQuery.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            "SELECT `foo` FROM `abc` UNION SELECT `bar` FROM `efg`",
            str(query1 + query2),
        )

    def test_union_as_subquery(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).union(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            'SELECT AVG("sq0"."t") FROM ((SELECT "t" FROM "abc") UNION (SELECT "t" FROM "efg")) "sq0"',
            str(q),
        )

    def test_union_with_no_quote_char(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).union(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            "SELECT AVG(sq0.t) FROM ((SELECT t FROM abc) UNION (SELECT t FROM efg)) sq0",
            q.get_sql(quote_char=None),
        )


class InsertQueryJoinTests(unittest.TestCase):
    def test_join_table_on_insert_query(self):
        a, b, c = Tables("a", "b", "c")
        q = (
            Query.into(c)
            .from_(a)
            .join(b)
            .on(a.fkey_id == b.id)
            .where(b.foo == 1)
            .select("a.*", "b.*")
        )

        self.assertEqual(
            'INSERT INTO "c" '
            'SELECT "a"."a.*","a"."b.*" '
            'FROM "a" JOIN "b" '
            'ON "a"."fkey_id"="b"."id" '
            'WHERE "b"."foo"=1',
            str(q),
        )


class UpdateQueryJoinTests(unittest.TestCase):
    def test_join_table_on_update_query(self):
        a, b = Tables("a", "b")
        q = (
            Query.update(a)
            .join(b)
            .on(a.fkey_id == b.id)
            .where(b.foo == 1)
            .set("adwords_batch_job_id", 1)
        )

        self.assertEqual(
            'UPDATE "a" '
            'JOIN "b" '
            'ON "a"."fkey_id"="b"."id" '
            'SET "adwords_batch_job_id"=1 '
            'WHERE "b"."foo"=1',
            str(q),
        )


class IntersectTests(unittest.TestCase):
    table1, table2 = Tables("abc", "efg")

    def test_intersect(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") INTERSECT (SELECT "bar" FROM "efg")',
            str(query1.intersect(query2)),
        )

    def test_intersect_multiple(self):
        table3, table4 = Tables("hij", "lmn")
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)
        query3 = Query.from_(table3).select(table3.baz)
        query4 = Query.from_(table4).select(table4.faz)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") INTERSECT '
            '(SELECT "bar" FROM "efg") INTERSECT '
            '(SELECT "baz" FROM "hij") INTERSECT '
            '(SELECT "faz" FROM "lmn")',
            str(query1.intersect(query2).intersect(query3).intersect(query4)),
        )

    def test_intersect_with_order_by(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        intersect_query = str((query1.intersect(query2)).orderby(query1.field("a")))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "INTERSECT "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "a"',
            intersect_query,
        )

    def test_intersect_with_limit(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        intersect_query = str((query1.intersect(query2)).limit(10))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "INTERSECT "
            '(SELECT "bar" "a" FROM "efg") '
            "LIMIT 10",
            intersect_query,
        )

    def test_intersect_with_offset(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        intersect_query = str((query1.intersect(query2)).offset(10))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "INTERSECT "
            '(SELECT "bar" "a" FROM "efg") '
            "OFFSET 10",
            intersect_query,
        )

    def test_require_equal_number_of_fields_intersect(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.fiz, self.table2.buz)

        with self.assertRaises(SetOperationException):
            str(query1.intersect(query2))

    def test_mysql_query_does_not_wrap_intersected_queries_with_params(self):
        query1 = MySQLQuery.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            "SELECT `foo` FROM `abc` INTERSECT SELECT `bar` FROM `efg`",
            str(query1.intersect(query2)),
        )

    def test_intersect_as_subquery(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).intersect(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            'SELECT AVG("sq0"."t") FROM ((SELECT "t" FROM "abc") INTERSECT (SELECT "t" FROM "efg")) "sq0"',
            str(q),
        )

    def test_intersect_with_no_quote_char(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).intersect(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            "SELECT AVG(sq0.t) FROM ((SELECT t FROM abc) INTERSECT (SELECT t FROM efg)) sq0",
            q.get_sql(quote_char=None),
        )


class MinusTests(unittest.TestCase):
    table1, table2 = Tables("abc", "efg")

    def test_minus(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") MINUS (SELECT "bar" FROM "efg")', str(query1.minus(query2))
        )

        self.assertEqual(
            '(SELECT "foo" FROM "abc") MINUS (SELECT "bar" FROM "efg")',
            str(query1 - query2),
        )

    def test_minus_multiple(self):
        table3, table4 = Tables("hij", "lmn")
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)
        query3 = Query.from_(table3).select(table3.baz)
        query4 = Query.from_(table4).select(table4.faz)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") MINUS '
            '(SELECT "bar" FROM "efg") MINUS '
            '(SELECT "baz" FROM "hij") MINUS '
            '(SELECT "faz" FROM "lmn")',
            str(query1 - query2 - query3 - query4),
        )

        self.assertEqual(
            '(SELECT "foo" FROM "abc") MINUS '
            '(SELECT "bar" FROM "efg") MINUS '
            '(SELECT "baz" FROM "hij") MINUS '
            '(SELECT "faz" FROM "lmn")',
            str(query1.minus(query2).minus(query3).minus(query4)),
        )

    def test_minus_with_order_by(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        minus_query = str(query1.minus(query2).orderby(query1.field("a")))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "MINUS "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "a"',
            minus_query,
        )

    def test_minus_query_with_order_by_use_minus_query_field(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        minus_query = query1.minus(query2)
        minus_query = str(minus_query.orderby(minus_query.field("b")))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "MINUS "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "b"',
            minus_query,
        )

    def test_require_equal_number_of_fields(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.fiz, self.table2.buz)

        with self.assertRaises(SetOperationException):
            str(query1.minus(query2))

    def test_mysql_query_does_not_wrap_minus_queries_with_params(self):
        query1 = MySQLQuery.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            "SELECT `foo` FROM `abc` MINUS SELECT `bar` FROM `efg`",
            str(query1 - query2),
        )

    def test_minus_as_subquery(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).minus(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            'SELECT AVG("sq0"."t") FROM ((SELECT "t" FROM "abc") MINUS (SELECT "t" FROM "efg")) "sq0"',
            str(q),
        )

    def test_minus_with_no_quote_char(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).minus(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            "SELECT AVG(sq0.t) FROM ((SELECT t FROM abc) MINUS (SELECT t FROM efg)) sq0",
            q.get_sql(quote_char=None),
        )


class ExceptOfTests(unittest.TestCase):
    table1, table2 = Tables("abc", "efg")

    def test_except(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") EXCEPT (SELECT "bar" FROM "efg")',
            str(query1.except_of(query2)),
        )

    def test_except_multiple(self):
        table3, table4 = Tables("hij", "lmn")
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.bar)
        query3 = Query.from_(table3).select(table3.baz)
        query4 = Query.from_(table4).select(table4.faz)

        self.assertEqual(
            '(SELECT "foo" FROM "abc") EXCEPT '
            '(SELECT "bar" FROM "efg") EXCEPT '
            '(SELECT "baz" FROM "hij") EXCEPT '
            '(SELECT "faz" FROM "lmn")',
            str(query1.except_of(query2).except_of(query3).except_of(query4)),
        )

    def test_except_with_order_by(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        except_query = str(query1.except_of(query2).orderby(query1.field("a")))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "EXCEPT "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "a"',
            except_query,
        )

    def test_except_query_with_order_by_use_minus_query_field(self):
        query1 = Query.from_(self.table1).select(self.table1.foo.as_("a"))
        query2 = Query.from_(self.table2).select(self.table2.bar.as_("a"))

        except_query = query1.except_of(query2)
        except_query = str(except_query.orderby(except_query.field("b")))

        self.assertEqual(
            '(SELECT "foo" "a" FROM "abc") '
            "EXCEPT "
            '(SELECT "bar" "a" FROM "efg") '
            'ORDER BY "b"',
            except_query,
        )

    def test_require_equal_number_of_fields_except_of(self):
        query1 = Query.from_(self.table1).select(self.table1.foo)
        query2 = Query.from_(self.table2).select(self.table2.fiz, self.table2.buz)

        with self.assertRaises(SetOperationException):
            str(query1.except_of(query2))

    def test_except_as_subquery(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).except_of(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            'SELECT AVG("sq0"."t") FROM ((SELECT "t" FROM "abc") EXCEPT (SELECT "t" FROM "efg")) "sq0"',
            str(q),
        )

    def test_except_with_no_quote_char(self):
        abc, efg = Tables("abc", "efg")
        hij = Query.from_(abc).select(abc.t).except_of(Query.from_(efg).select(efg.t))
        q = Query.from_(hij).select(fn.Avg(hij.t))

        self.assertEqual(
            "SELECT AVG(sq0.t) FROM ((SELECT t FROM abc) EXCEPT (SELECT t FROM efg)) sq0",
            q.get_sql(quote_char=None),
        )
