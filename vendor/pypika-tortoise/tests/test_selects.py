import unittest

from pypika import SYSTEM_TIME, AliasedQuery, Case, EmptyCriterion
from pypika import Field as F
from pypika import (
    Index,
    MySQLQuery,
    NullValue,
    Order,
    PostgreSQLQuery,
    Query,
    QueryException,
    SQLLiteQuery,
    Table,
    Tables,
)
from pypika import functions as fn
from pypika.terms import Field, ValueWrapper

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"


class SelectTests(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_empty_query(self):
        q = Query.from_("abc")

        self.assertEqual("", str(q))

    def test_select_no_from(self):
        q = Query.select(1)

        self.assertEqual("SELECT 1", str(q))

    def test_select_no_with_alias_from(self):
        q = Query.select(ValueWrapper(1, "test"))

        self.assertEqual('SELECT 1 "test"', str(q))

    def test_select_no_from_with_field_raises_exception(self):
        with self.assertRaises(QueryException):
            Query.select("asdf")

    def test_select__star(self):
        q = Query.from_("abc").select("*")

        self.assertEqual('SELECT * FROM "abc"', str(q))

    def test_select__table_schema(self):
        q = Query.from_(Table("abc", "schema1")).select("*")

        self.assertEqual('SELECT * FROM "schema1"."abc"', str(q))

    def test_select__table_schema_with_multiple_levels_as_tuple(self):
        q = Query.from_(Table("abc", ("schema1", "schema2"))).select("*")

        self.assertEqual('SELECT * FROM "schema1"."schema2"."abc"', str(q))

    def test_select__table_schema_with_multiple_levels_as_list(self):
        q = Query.from_(Table("abc", ["schema1", "schema2"])).select("*")

        self.assertEqual('SELECT * FROM "schema1"."schema2"."abc"', str(q))

    def test_select__star__replacement(self):
        q = Query.from_("abc").select("foo").select("*")

        self.assertEqual('SELECT * FROM "abc"', str(q))

    def test_select__distinct__single(self):
        q = Query.from_("abc").select("foo").distinct()

        self.assertEqual('SELECT DISTINCT "foo" FROM "abc"', str(q))

    def test_select__distinct__multi(self):
        q = Query.from_("abc").select("foo", "bar").distinct()

        self.assertEqual('SELECT DISTINCT "foo","bar" FROM "abc"', str(q))

    def test_select__column__single__str(self):
        q = Query.from_("abc").select("foo")

        self.assertEqual('SELECT "foo" FROM "abc"', str(q))

    def test_select__column__single__alias__str(self):
        q = Query.from_(self.table_abc).select(self.table_abc.foo.as_("bar"))

        self.assertEqual('SELECT "foo" "bar" FROM "abc"', str(q))

    def test_select__column__single__table_alias__str(self):
        q = Query.from_(self.table_abc.as_("fizzbuzz")).select(self.table_abc.foo.as_("bar"))

        self.assertEqual('SELECT "foo" "bar" FROM "abc" "fizzbuzz"', str(q))

    def test_select__column__single__field(self):
        t = Table("abc")
        q = Query.from_(t).select(t.foo)

        self.assertEqual('SELECT "foo" FROM "abc"', str(q))

    def test_select__columns__multi__str(self):
        q1 = Query.from_("abc").select("foo", "bar")
        q2 = Query.from_("abc").select("foo").select("bar")

        self.assertEqual('SELECT "foo","bar" FROM "abc"', str(q1))
        self.assertEqual('SELECT "foo","bar" FROM "abc"', str(q2))

    def test_select__columns__multi__field(self):
        q1 = Query.from_(self.table_abc).select(self.table_abc.foo, self.table_abc.bar)
        q2 = Query.from_(self.table_abc).select(self.table_abc.foo).select(self.table_abc.bar)

        self.assertEqual('SELECT "foo","bar" FROM "abc"', str(q1))
        self.assertEqual('SELECT "foo","bar" FROM "abc"', str(q2))

    def test_select__multiple_tables(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo)
            .from_(self.table_efg)
            .select(self.table_efg.bar)
        )

        self.assertEqual('SELECT "abc"."foo","efg"."bar" FROM "abc","efg"', str(q))

    def test_select__subquery(self):
        subquery = Query.from_(self.table_abc).select("*")
        q = Query.from_(subquery).select(subquery.foo, subquery.bar)

        self.assertEqual(
            'SELECT "sq0"."foo","sq0"."bar" ' 'FROM (SELECT * FROM "abc") "sq0"', str(q)
        )

    def test_select__multiple_subqueries(self):
        subquery0 = Query.from_(self.table_abc).select("foo")
        subquery1 = Query.from_(self.table_efg).select("bar")
        q = Query.from_(subquery0).from_(subquery1).select(subquery0.foo, subquery1.bar)

        self.assertEqual(
            'SELECT "sq0"."foo","sq1"."bar" '
            'FROM (SELECT "foo" FROM "abc") "sq0",'
            '(SELECT "bar" FROM "efg") "sq1"',
            str(q),
        )

    def test_select__nested_subquery(self):
        subquery0 = Query.from_(self.table_abc).select("*")
        subquery1 = Query.from_(subquery0).select(subquery0.foo, subquery0.bar)
        subquery2 = Query.from_(subquery1).select(subquery1.foo)

        q = Query.from_(subquery2).select(subquery2.foo)

        self.assertEqual(
            'SELECT "sq2"."foo" '
            'FROM (SELECT "sq1"."foo" '
            'FROM (SELECT "sq0"."foo","sq0"."bar" '
            'FROM (SELECT * FROM "abc") "sq0") "sq1") "sq2"',
            str(q),
        )

    def test_select__no_table(self):
        q = Query.select(1, 2, 3)

        self.assertEqual("SELECT 1,2,3", str(q))

    def test_select_then_add_table(self):
        q = Query.select(1).select(2, 3).from_("abc").select("foo")

        self.assertEqual('SELECT 1,2,3,"foo" FROM "abc"', str(q))

    def test_select_with_limit(self):
        q1 = Query.from_("abc").select("foo")[:10]

        self.assertEqual('SELECT "foo" FROM "abc" LIMIT 10', str(q1))

    def test_select_with_limit_zero(self):
        with self.subTest("using python slice"):
            q1 = Query.from_("abc").select("foo")[:0]
            self.assertEqual('SELECT "foo" FROM "abc" LIMIT 0', str(q1))

        with self.subTest("using limit method"):
            q2 = Query.from_("abc").select("foo").limit(0)
            self.assertEqual('SELECT "foo" FROM "abc" LIMIT 0', str(q2))

    def test_select_with_limit__func(self):
        q1 = Query.from_("abc").select("foo").limit(10)

        self.assertEqual('SELECT "foo" FROM "abc" LIMIT 10', str(q1))

    def test_select_with_offset(self):
        q1 = Query.from_("abc").select("foo")[10:]

        self.assertEqual('SELECT "foo" FROM "abc" OFFSET 10', str(q1))

    def test_select_with_offset__func(self):
        q1 = Query.from_("abc").select("foo").offset(10)

        self.assertEqual('SELECT "foo" FROM "abc" OFFSET 10', str(q1))

    def test_select_with_limit_and_offset(self):
        q1 = Query.from_("abc").select("foo")[10:10]

        self.assertEqual('SELECT "foo" FROM "abc" LIMIT 10 OFFSET 10', str(q1))

    def test_select_with_force_index(self):
        q = Query.from_("abc").select("foo").force_index("egg")

        self.assertEqual('SELECT "foo" FROM "abc" FORCE INDEX ("egg")', str(q))

    def test_select_with_force_index_with_index_object(self):
        index = Index("egg")
        q = Query.from_("abc").select("foo").force_index(index)

        self.assertEqual('SELECT "foo" FROM "abc" FORCE INDEX ("egg")', str(q))

    def test_select_with_force_index_multiple_indexes(self):
        q = Query.from_("abc").select("foo").force_index("egg", "bacon")

        self.assertEqual('SELECT "foo" FROM "abc" FORCE INDEX ("egg","bacon")', str(q))

    def test_select_with_force_index_multiple_calls(self):
        q = (
            Query.from_("abc")
            .select("foo")
            .force_index(
                "egg",
            )
            .force_index("spam")
        )

        self.assertEqual('SELECT "foo" FROM "abc" FORCE INDEX ("egg","spam")', str(q))

    def test_select_with_use_index(self):
        q = Query.from_("abc").select("foo").use_index("egg")

        self.assertEqual('SELECT "foo" FROM "abc" USE INDEX ("egg")', str(q))

    def test_select_with_use_index_with_index_object(self):
        index = Index("egg")
        q = Query.from_("abc").select("foo").use_index(index)

        self.assertEqual('SELECT "foo" FROM "abc" USE INDEX ("egg")', str(q))

    def test_select_with_use_index_multiple_indexes(self):
        q = Query.from_("abc").select("foo").use_index("egg", "bacon")

        self.assertEqual('SELECT "foo" FROM "abc" USE INDEX ("egg","bacon")', str(q))

    def test_select_with_use_index_multiple_calls(self):
        q = (
            Query.from_("abc")
            .select("foo")
            .use_index(
                "egg",
            )
            .use_index("spam")
        )

        self.assertEqual('SELECT "foo" FROM "abc" USE INDEX ("egg","spam")', str(q))

    def test_mysql_query_uses_backtick_quote_chars(self):
        q = MySQLQuery.from_("abc").select("foo", "bar")

        self.assertEqual("SELECT `foo`,`bar` FROM `abc`", str(q))

    def test_postgresql_query_uses_double_quote_chars(self):
        q = PostgreSQLQuery.from_("abc").select("foo", "bar")

        self.assertEqual('SELECT "foo","bar" FROM "abc"', str(q))

    def test_table_select_alias(self):
        q = self.table_abc.select(1)

        self.assertEqual('SELECT 1 FROM "abc"', str(q))
        self.assertEqual(q, Query.from_("abc").select(1))

    def test_table_select_alias_with_offset_and_limit(self):
        self.assertEqual(
            self.table_abc.select("foo")[10:10], Query.from_("abc").select("foo")[10:10]
        )
        self.assertEqual(
            self.table_abc.select(self.table_abc.foo)[10:10],
            Query.from_("abc").select("foo")[10:10],
        )

    def test_temporal_select(self):
        t = Table("abc")

        with self.subTest("with system time as of"):
            q = Query.from_(t.for_(SYSTEM_TIME.as_of("2020-01-01"))).select("*")

            self.assertEqual("SELECT * FROM \"abc\" FOR SYSTEM_TIME AS OF '2020-01-01'", str(q))

        with self.subTest("with system time between"):
            q = Query.from_(t.for_(SYSTEM_TIME.between("2020-01-01", "2020-02-01"))).select("*")

            self.assertEqual(
                "SELECT * FROM \"abc\" FOR SYSTEM_TIME BETWEEN '2020-01-01' AND '2020-02-01'",
                str(q),
            )

        with self.subTest("with system time from to"):
            q = Query.from_(t.for_(SYSTEM_TIME.from_to("2020-01-01", "2020-02-01"))).select("*")

            self.assertEqual(
                "SELECT * FROM \"abc\" FOR SYSTEM_TIME FROM '2020-01-01' TO '2020-02-01'",
                str(q),
            )

        with self.subTest("with ALL"):
            q = Query.from_(t.for_(SYSTEM_TIME.all_())).select("*")

            self.assertEqual('SELECT * FROM "abc" FOR SYSTEM_TIME ALL', str(q))

        with self.subTest("with period between"):
            q = Query.from_(t.for_(t.valid_period.between("2020-01-01", "2020-02-01"))).select("*")

            self.assertEqual(
                "SELECT * FROM \"abc\" FOR \"valid_period\" BETWEEN '2020-01-01' AND '2020-02-01'",
                str(q),
            )

        with self.subTest("with period from to"):
            q = Query.from_(t.for_(t.valid_period.from_to("2020-01-01", "2020-02-01"))).select("*")

            self.assertEqual(
                "SELECT * FROM \"abc\" FOR \"valid_period\" FROM '2020-01-01' TO '2020-02-01'",
                str(q),
            )

        with self.subTest("with ALL"):
            q = Query.from_(t.for_(t.valid_period.all_())).select("*")

            self.assertEqual('SELECT * FROM "abc" FOR "valid_period" ALL', str(q))


class WhereTests(unittest.TestCase):
    t = Table("abc")
    t2 = Table("cba")

    def test_where_field_equals(self):
        q1 = Query.from_(self.t).select("*").where(self.t.foo == self.t.bar)
        q2 = Query.from_(self.t).select("*").where(self.t.foo.eq(self.t.bar))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo"="bar"', str(q1))
        self.assertEqual('SELECT * FROM "abc" WHERE "foo"="bar"', str(q2))
        q = self.t.select("*").where(self.t.foo == self.t.bar)
        self.assertEqual(q, q1)

    def test_where_field_equals_for_update(self):
        q = Query.from_(self.t).select("*").where(self.t.foo == self.t.bar).for_update()
        self.assertEqual('SELECT * FROM "abc" WHERE "foo"="bar" FOR UPDATE', str(q))

    def test_where_field_equals_for_update_nowait(self):
        q = Query.from_(self.t).select("*").where(self.t.foo == self.t.bar).for_update(nowait=True)
        self.assertEqual('SELECT * FROM "abc" WHERE "foo"="bar" FOR UPDATE NOWAIT', str(q))

    def test_where_field_equals_for_update_skip_locked(self):
        q = (
            Query.from_(self.t)
            .select("*")
            .where(self.t.foo == self.t.bar)
            .for_update(skip_locked=True)
        )
        self.assertEqual('SELECT * FROM "abc" WHERE "foo"="bar" FOR UPDATE SKIP LOCKED', str(q))

    def test_where_field_equals_for_update_of(self):
        q = Query.from_(self.t).select("*").where(self.t.foo == self.t.bar).for_update(of=("abc",))
        self.assertEqual('SELECT * FROM "abc" WHERE "foo"="bar" FOR UPDATE OF "abc"', str(q))

    def test_where_field_equals_for_update_of_multiple_tables(self):
        q = (
            Query.from_(self.t)
            .join(self.t2)
            .on(self.t.id == self.t2.abc_id)
            .select("*")
            .where(self.t.foo == self.t.bar)
            .for_update(of=("abc", "cba"))
        )
        self.assertIn(
            str(q),
            [
                'SELECT * FROM "abc" JOIN "cba" ON "abc"."id"="cba"."abc_id" WHERE '
                '"abc"."foo"="abc"."bar" FOR UPDATE OF "cba", "abc"',
                'SELECT * FROM "abc" JOIN "cba" ON "abc"."id"="cba"."abc_id" WHERE '
                '"abc"."foo"="abc"."bar" FOR UPDATE OF "abc", "cba"',
            ],
        )

    def test_where_field_equals_for_update_all(self):
        q = (
            Query.from_(self.t)
            .select("*")
            .where(self.t.foo == self.t.bar)
            .for_update(nowait=True, skip_locked=True, of=("abc",))
        )
        self.assertEqual('SELECT * FROM "abc" WHERE "foo"="bar" FOR UPDATE OF "abc" NOWAIT', str(q))

    def test_where_field_equals_for_update_skip_locked_and_of(self):
        q = (
            Query.from_(self.t)
            .select("*")
            .where(self.t.foo == self.t.bar)
            .for_update(nowait=False, skip_locked=True, of=("abc",))
        )
        self.assertEqual(
            'SELECT * FROM "abc" WHERE "foo"="bar" FOR UPDATE OF "abc" SKIP LOCKED',
            str(q),
        )

    def test_where_field_equals_where(self):
        q = Query.from_(self.t).select("*").where(self.t.foo == 1).where(self.t.bar == self.t.baz)

        self.assertEqual('SELECT * FROM "abc" WHERE "foo"=1 AND "bar"="baz"', str(q))

    def test_where_field_equals_where_not(self):
        q = (
            Query.from_(self.t)
            .select("*")
            .where((self.t.foo == 1).negate())
            .where(self.t.bar == self.t.baz)
        )

        self.assertEqual('SELECT * FROM "abc" WHERE NOT "foo"=1 AND "bar"="baz"', str(q))

    def test_where_field_equals_where_two_not(self):
        q = (
            Query.from_(self.t)
            .select("*")
            .where((self.t.foo == 1).negate())
            .where((self.t.bar == self.t.baz).negate())
        )

        self.assertEqual('SELECT * FROM "abc" WHERE NOT "foo"=1 AND NOT "bar"="baz"', str(q))

    def test_where_single_quote(self):
        q1 = Query.from_(self.t).select("*").where(self.t.foo == "bar'foo")

        self.assertEqual("SELECT * FROM \"abc\" WHERE \"foo\"='bar''foo'", str(q1))

    def test_where_field_equals_and(self):
        q = Query.from_(self.t).select("*").where((self.t.foo == 1) & (self.t.bar == self.t.baz))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo"=1 AND "bar"="baz"', str(q))

    def test_where_field_equals_or(self):
        q = Query.from_(self.t).select("*").where((self.t.foo == 1) | (self.t.bar == self.t.baz))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo"=1 OR "bar"="baz"', str(q))

    def test_where_nested_conditions(self):
        q = (
            Query.from_(self.t)
            .select("*")
            .where((self.t.foo == 1) | (self.t.bar == self.t.baz))
            .where(self.t.baz == 0)
        )

        self.assertEqual('SELECT * FROM "abc" WHERE ("foo"=1 OR "bar"="baz") AND "baz"=0', str(q))

    def test_where_field_starts_with(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.like("ab%"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" LIKE \'ab%\'', str(q))

    def test_where_field_contains(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.like("%fg%"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" LIKE \'%fg%\'', str(q))

    def test_where_field_ends_with(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.like("%yz"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" LIKE \'%yz\'', str(q))

    def test_where_field_is_n_chars_long(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.like("___"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" LIKE \'___\'', str(q))

    def test_where_field_does_not_start_with(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.not_like("ab%"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" NOT LIKE \'ab%\'', str(q))

    def test_where_field_does_not_contain(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.not_like("%fg%"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" NOT LIKE \'%fg%\'', str(q))

    def test_where_field_does_not_end_with(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.not_like("%yz"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" NOT LIKE \'%yz\'', str(q))

    def test_where_field_is_not_n_chars_long(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.not_like("___"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" NOT LIKE \'___\'', str(q))

    def test_where_field_matches_regex(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.regex(r"^b"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" REGEX \'^b\'', str(q))

    def test_where_field_matches_rlike(self):
        q = Query.from_(self.t).select(self.t.star).where(self.t.foo.rlike(r"^b"))

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" RLIKE \'^b\'', str(q))

    def test_ignore_empty_criterion(self):
        q1 = Query.from_(self.t).select("*").where(EmptyCriterion())

        self.assertEqual('SELECT * FROM "abc"', str(q1))

    def test_select_with_force_index_and_where(self):
        q = Query.from_("abc").select("foo").where(self.t.foo == self.t.bar).force_index("egg")

        self.assertEqual('SELECT "foo" FROM "abc" FORCE INDEX ("egg") WHERE "foo"="bar"', str(q))


class PreWhereTests(WhereTests):
    t = Table("abc")

    def test_prewhere_field_equals(self):
        q1 = Query.from_(self.t).select("*").prewhere(self.t.foo == self.t.bar)
        q2 = Query.from_(self.t).select("*").prewhere(self.t.foo.eq(self.t.bar))

        self.assertEqual('SELECT * FROM "abc" PREWHERE "foo"="bar"', str(q1))
        self.assertEqual('SELECT * FROM "abc" PREWHERE "foo"="bar"', str(q2))

    def test_where_and_prewhere(self):
        q = (
            Query.from_(self.t)
            .select("*")
            .prewhere(self.t.foo == self.t.bar)
            .where(self.t.foo == self.t.bar)
        )

        self.assertEqual('SELECT * FROM "abc" PREWHERE "foo"="bar" WHERE "foo"="bar"', str(q))


class GroupByTests(unittest.TestCase):
    t = Table("abc")
    maxDiff = None

    def test_groupby__single(self):
        q = Query.from_(self.t).groupby(self.t.foo).select(self.t.foo)

        self.assertEqual('SELECT "foo" FROM "abc" GROUP BY "foo"', str(q))

    def test_groupby__multi(self):
        q = Query.from_(self.t).groupby(self.t.foo, self.t.bar).select(self.t.foo, self.t.bar)

        self.assertEqual('SELECT "foo","bar" FROM "abc" GROUP BY "foo","bar"', str(q))

    def test_groupby__count_star(self):
        q = Query.from_(self.t).groupby(self.t.foo).select(self.t.foo, fn.Count("*"))

        self.assertEqual('SELECT "foo",COUNT(*) FROM "abc" GROUP BY "foo"', str(q))

    def test_groupby__count_field(self):
        q = Query.from_(self.t).groupby(self.t.foo).select(self.t.foo, fn.Count(self.t.bar))

        self.assertEqual('SELECT "foo",COUNT("bar") FROM "abc" GROUP BY "foo"', str(q))

    def test_groupby__count_distinct(self):
        q = Query.from_(self.t).groupby(self.t.foo).select(self.t.foo, fn.Count("*").distinct())

        self.assertEqual('SELECT "foo",COUNT(DISTINCT *) FROM "abc" GROUP BY "foo"', str(q))

    def test_groupby__sum_distinct(self):
        q = (
            Query.from_(self.t)
            .groupby(self.t.foo)
            .select(self.t.foo, fn.Sum(self.t.bar).distinct())
        )

        self.assertEqual('SELECT "foo",SUM(DISTINCT "bar") FROM "abc" GROUP BY "foo"', str(q))

    def test_groupby__sum_filter(self):
        q = (
            Query.from_(self.t)
            .groupby(self.t.foo)
            .select(
                self.t.foo,
                fn.Sum(self.t.bar).filter(self.t.id.eq(1) & self.t.cid.gt(2)),
            )
        )

        self.assertEqual(
            'SELECT "foo",SUM("bar") FILTER(WHERE "id"=1 AND "cid">2) FROM "abc" GROUP BY "foo"',
            str(q),
        )

    def test_groupby__str(self):
        q = Query.from_("abc").groupby("foo").select("foo", fn.Count("*").distinct())

        self.assertEqual('SELECT "foo",COUNT(DISTINCT *) FROM "abc" GROUP BY "foo"', str(q))

    def test_groupby__int(self):
        q = Query.from_("abc").groupby(1).select("foo", fn.Count("*").distinct())

        self.assertEqual('SELECT "foo",COUNT(DISTINCT *) FROM "abc" GROUP BY 1', str(q))

    def test_groupby__alias(self):
        bar = self.t.bar.as_("bar01")
        q = Query.from_(self.t).select(fn.Sum(self.t.foo), bar).groupby(bar)

        self.assertEqual('SELECT SUM("foo"),"bar" "bar01" FROM "abc" GROUP BY "bar01"', str(q))

    def test_groupby__no_alias(self):
        bar = self.t.bar.as_("bar01")
        q = Query.from_(self.t).select(fn.Sum(self.t.foo), bar).groupby(bar)

        self.assertEqual(
            'SELECT SUM("foo"),"bar" "bar01" FROM "abc" GROUP BY "bar"',
            q.get_sql(groupby_alias=False),
        )

    def test_groupby__alias_platforms(self):
        bar = self.t.bar.as_("bar01")

        for query_cls in [
            MySQLQuery,
            PostgreSQLQuery,
            SQLLiteQuery,
        ]:
            q = query_cls.from_(self.t).select(fn.Sum(self.t.foo), bar).groupby(bar)

            quote_char = (
                query_cls._builder().QUOTE_CHAR
                if isinstance(query_cls._builder().QUOTE_CHAR, str)
                else '"'
            )

            self.assertEqual(
                "SELECT "
                "SUM({quote_char}foo{quote_char}),"
                "{quote_char}bar{quote_char}{as_keyword}{quote_char}bar01{quote_char} "
                "FROM {quote_char}abc{quote_char} "
                "GROUP BY {quote_char}bar01{quote_char}".format(
                    as_keyword=" ",
                    quote_char=quote_char,
                ),
                str(q),
            )

    def test_groupby__alias_with_join(self):
        table1 = Table("table1", alias="t1")
        bar = table1.bar.as_("bar01")
        q = (
            Query.from_(self.t)
            .join(table1)
            .on(self.t.id == table1.t_ref)
            .select(fn.Sum(self.t.foo), bar)
            .groupby(bar)
        )

        self.assertEqual(
            'SELECT SUM("abc"."foo"),"t1"."bar" "bar01" FROM "abc" '
            'JOIN "table1" "t1" ON "abc"."id"="t1"."t_ref" '
            'GROUP BY "bar01"',
            str(q),
        )

    def test_groupby_with_case_uses_the_alias(self):
        q = (
            Query.from_(self.t)
            .select(
                fn.Sum(self.t.foo).as_("bar"),
                Case()
                .when(self.t.fname == "Tom", "It was Tom")
                .else_("It was someone else.")
                .as_("who_was_it"),
            )
            .groupby(
                Case()
                .when(self.t.fname == "Tom", "It was Tom")
                .else_("It was someone else.")
                .as_("who_was_it")
            )
        )

        self.assertEqual(
            'SELECT SUM("foo") "bar",'
            "CASE WHEN \"fname\"='Tom' THEN 'It was Tom' "
            "ELSE 'It was someone else.' END \"who_was_it\" "
            'FROM "abc" '
            'GROUP BY "who_was_it"',
            str(q),
        )

    def test_mysql_query_uses_backtick_quote_chars(self):
        q = MySQLQuery.from_(self.t).groupby(self.t.foo).select(self.t.foo)

        self.assertEqual("SELECT `foo` FROM `abc` GROUP BY `foo`", str(q))

    def test_postgres_query_uses_double_quote_chars(self):
        q = PostgreSQLQuery.from_(self.t).groupby(self.t.foo).select(self.t.foo)

        self.assertEqual('SELECT "foo" FROM "abc" GROUP BY "foo"', str(q))

    def test_group_by__single_with_totals(self):
        q = Query.from_(self.t).groupby(self.t.foo).select(self.t.foo).with_totals()

        self.assertEqual('SELECT "foo" FROM "abc" GROUP BY "foo" WITH TOTALS', str(q))

    def test_groupby__multi_with_totals(self):
        q = (
            Query.from_(self.t)
            .groupby(self.t.foo, self.t.bar)
            .select(self.t.foo, self.t.bar)
            .with_totals()
        )

        self.assertEqual('SELECT "foo","bar" FROM "abc" GROUP BY "foo","bar" WITH TOTALS', str(q))


class HavingTests(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_having_greater_than(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, fn.Sum(self.table_abc.bar))
            .groupby(self.table_abc.foo)
            .having(fn.Sum(self.table_abc.bar) > 1)
        )

        self.assertEqual(
            'SELECT "foo",SUM("bar") FROM "abc" GROUP BY "foo" HAVING SUM("bar")>1',
            str(q),
        )

    def test_having_and(self):
        q = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, fn.Sum(self.table_abc.bar))
            .groupby(self.table_abc.foo)
            .having((fn.Sum(self.table_abc.bar) > 1) & (fn.Sum(self.table_abc.bar) < 100))
        )

        self.assertEqual(
            'SELECT "foo",SUM("bar") FROM "abc" GROUP BY "foo" HAVING SUM("bar")>1 AND SUM("bar")<100',
            str(q),
        )

    def test_having_join_and_equality(self):
        q = (
            Query.from_(self.table_abc)
            .join(self.table_efg)
            .on(self.table_abc.foo == self.table_efg.foo)
            .select(self.table_abc.foo, fn.Sum(self.table_efg.bar), self.table_abc.buz)
            .groupby(self.table_abc.foo)
            .having(self.table_abc.buz == "fiz")
            .having(fn.Sum(self.table_efg.bar) > 100)
        )

        self.assertEqual(
            'SELECT "abc"."foo",SUM("efg"."bar"),"abc"."buz" FROM "abc" '
            'JOIN "efg" ON "abc"."foo"="efg"."foo" '
            'GROUP BY "abc"."foo" '
            'HAVING "abc"."buz"=\'fiz\' AND SUM("efg"."bar")>100',
            str(q),
        )

    def test_mysql_query_uses_backtick_quote_chars(self):
        q = (
            MySQLQuery.from_(self.table_abc)
            .select(self.table_abc.foo)
            .groupby(self.table_abc.foo)
            .having(self.table_abc.buz == "fiz")
        )
        self.assertEqual("SELECT `foo` FROM `abc` GROUP BY `foo` HAVING `buz`='fiz'", str(q))

    def test_postgres_query_uses_double_quote_chars(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select(self.table_abc.foo)
            .groupby(self.table_abc.foo)
            .having(self.table_abc.buz == "fiz")
        )
        self.assertEqual('SELECT "foo" FROM "abc" GROUP BY "foo" HAVING "buz"=\'fiz\'', str(q))


class OrderByTests(unittest.TestCase):
    t = Table("abc")

    def test_orderby_single_field(self):
        q = Query.from_(self.t).orderby(self.t.foo).select(self.t.foo)

        self.assertEqual('SELECT "foo" FROM "abc" ORDER BY "foo"', str(q))

    def test_orderby_multi_fields(self):
        q = Query.from_(self.t).orderby(self.t.foo, self.t.bar).select(self.t.foo, self.t.bar)

        self.assertEqual('SELECT "foo","bar" FROM "abc" ORDER BY "foo","bar"', str(q))

    def test_orderby_single_str(self):
        q = Query.from_("abc").orderby("foo").select("foo")

        self.assertEqual('SELECT "foo" FROM "abc" ORDER BY "foo"', str(q))

    def test_orderby_asc(self):
        q = Query.from_(self.t).orderby(self.t.foo, order=Order.asc).select(self.t.foo)

        self.assertEqual('SELECT "foo" FROM "abc" ORDER BY "foo" ASC', str(q))

    def test_orderby_desc(self):
        q = Query.from_(self.t).orderby(self.t.foo, order=Order.desc).select(self.t.foo)

        self.assertEqual('SELECT "foo" FROM "abc" ORDER BY "foo" DESC', str(q))

    def test_orderby_no_alias(self):
        bar = self.t.bar.as_("bar01")
        q = Query.from_(self.t).select(fn.Sum(self.t.foo), bar).orderby(bar)

        self.assertEqual(
            'SELECT SUM("foo"),"bar" "bar01" FROM "abc" ORDER BY "bar"',
            q.get_sql(orderby_alias=False),
        )

    def test_orderby_alias(self):
        bar = self.t.bar.as_("bar01")
        q = Query.from_(self.t).select(fn.Sum(self.t.foo), bar).orderby(bar)

        self.assertEqual('SELECT SUM("foo"),"bar" "bar01" FROM "abc" ORDER BY "bar01"', q.get_sql())


class AliasTests(unittest.TestCase):
    t = Table("abc")

    def test_table_field(self):
        q = Query.from_(self.t).select(self.t.foo.as_("bar"))

        self.assertEqual('SELECT "foo" "bar" FROM "abc"', str(q))

    def test_table_field__multi(self):
        q = Query.from_(self.t).select(self.t.foo.as_("bar"), self.t.fiz.as_("buz"))

        self.assertEqual('SELECT "foo" "bar","fiz" "buz" FROM "abc"', str(q))

    def test_arithmetic_function(self):
        q = Query.from_(self.t).select((self.t.foo + self.t.bar).as_("biz"))

        self.assertEqual('SELECT "foo"+"bar" "biz" FROM "abc"', str(q))

    def test_functions_using_as(self):
        q = Query.from_(self.t).select(fn.Count("*").as_("foo"))

        self.assertEqual('SELECT COUNT(*) "foo" FROM "abc"', str(q))

    def test_functions_using_constructor_param(self):
        q = Query.from_(self.t).select(fn.Count("*", alias="foo"))

        self.assertEqual('SELECT COUNT(*) "foo" FROM "abc"', str(q))

    def test_function_using_as_nested(self):
        """
        We don't show aliases of fields that are arguments of a function.
        """
        q = Query.from_(self.t).select(fn.Sqrt(fn.Count("*").as_("foo")).as_("bar"))

        self.assertEqual('SELECT SQRT(COUNT(*)) "bar" FROM "abc"', str(q))

    def test_functions_using_constructor_param_nested(self):
        """
        We don't show aliases of fields that are arguments of a function.
        """
        q = Query.from_(self.t).select(fn.Sqrt(fn.Count("*", alias="foo"), alias="bar"))

        self.assertEqual('SELECT SQRT(COUNT(*)) "bar" FROM "abc"', str(q))

    def test_ignored_in_where(self):
        q = Query.from_(self.t).select(self.t.foo).where(self.t.foo.as_("bar") == 1)

        self.assertEqual('SELECT "foo" FROM "abc" WHERE "foo"=1', str(q))

    def test_ignored_in_groupby(self):
        q = Query.from_(self.t).select(self.t.foo).groupby(self.t.foo.as_("bar"))

        self.assertEqual('SELECT "foo" FROM "abc" GROUP BY "foo"', str(q))

    def test_ignored_in_orderby(self):
        q = Query.from_(self.t).select(self.t.foo).orderby(self.t.foo.as_("bar"))

        self.assertEqual('SELECT "foo" FROM "abc" ORDER BY "foo"', str(q))

    def test_ignored_in_criterion(self):
        c = self.t.foo.as_("bar") == 1

        self.assertEqual('"foo"=1', str(c))

    def test_ignored_in_criterion_comparison(self):
        c = self.t.foo.as_("bar") == self.t.fiz.as_("buz")

        self.assertEqual('"foo"="fiz"', str(c))

    def test_ignored_in_field_inside_case(self):
        q = Query.from_(self.t).select(
            Case().when(self.t.foo == 1, "a").else_(self.t.bar.as_('"buz"'))
        )

        self.assertEqual('SELECT CASE WHEN "foo"=1 THEN \'a\' ELSE "bar" END FROM "abc"', str(q))

    def test_case_using_as(self):
        q = Query.from_(self.t).select(Case().when(self.t.foo == 1, "a").else_("b").as_("bar"))

        self.assertEqual(
            'SELECT CASE WHEN "foo"=1 THEN \'a\' ELSE \'b\' END "bar" FROM "abc"',
            str(q),
        )

    def test_case_using_constructor_param(self):
        q = Query.from_(self.t).select(Case(alias="bar").when(self.t.foo == 1, "a").else_("b"))

        self.assertEqual(
            'SELECT CASE WHEN "foo"=1 THEN \'a\' ELSE \'b\' END "bar" FROM "abc"',
            str(q),
        )

    def test_select__multiple_tables(self):
        table_abc, table_efg = Table("abc", alias="q0"), Table("efg", alias="q1")

        q = Query.from_(table_abc).select(table_abc.foo).from_(table_efg).select(table_efg.bar)

        self.assertEqual('SELECT "q0"."foo","q1"."bar" FROM "abc" "q0","efg" "q1"', str(q))

    def test_use_aliases_in_groupby_and_orderby(self):
        table_abc = Table("abc", alias="q0")

        my_foo = table_abc.foo.as_("my_foo")
        q = Query.from_(table_abc).select(my_foo, table_abc.bar).groupby(my_foo).orderby(my_foo)

        self.assertEqual(
            'SELECT "q0"."foo" "my_foo","q0"."bar" '
            'FROM "abc" "q0" '
            'GROUP BY "my_foo" '
            'ORDER BY "my_foo"',
            str(q),
        )

    def test_table_with_schema_and_alias(self):
        table = Table("abc", schema="schema", alias="alias")
        self.assertEqual('"schema"."abc" "alias"', str(table))

    def test_null_value_with_alias(self):
        q = Query.select(NullValue().as_("abcdef"))

        self.assertEqual('SELECT NULL "abcdef"', str(q))


class SubqueryTests(unittest.TestCase):
    maxDiff = None

    table_abc, table_efg, table_hij = Tables("abc", "efg", "hij")

    def test_where__in(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(
                self.table_abc.foo.isin(
                    Query.from_(self.table_efg)
                    .select(self.table_efg.foo)
                    .where(self.table_efg.bar == 0)
                )
            )
        )

        self.assertEqual(
            'SELECT * FROM "abc" WHERE "foo" IN (SELECT "foo" FROM "efg" WHERE "bar"=0)',
            str(q),
        )

    def test_where__in_nested(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.foo)
            .isin(self.table_efg.select("*"))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "foo" IN (SELECT * FROM "efg")', str(q))

    def test_join(self):
        subquery = Query.from_("efg").select("fiz", "buz").where(F("buz") == 0)

        q = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(self.table_abc.bar == subquery.buz)
            .select(self.table_abc.foo, subquery.fiz)
        )

        self.assertEqual(
            'SELECT "abc"."foo","sq0"."fiz" FROM "abc" '
            'JOIN (SELECT "fiz","buz" FROM "efg" WHERE "buz"=0) "sq0" '
            'ON "abc"."bar"="sq0"."buz"',
            str(q),
        )

    def test_select_subquery(self):
        subq = Query.from_(self.table_efg).select("fizzbuzz").where(self.table_efg.id == 1)

        q = Query.from_(self.table_abc).select("foo", "bar").select(subq)

        self.assertEqual(
            'SELECT "foo","bar",(SELECT "fizzbuzz" FROM "efg" WHERE "id"=1) ' 'FROM "abc"',
            str(q),
        )

    def test_select_subquery_with_alias(self):
        subq = Query.from_(self.table_efg).select("fizzbuzz").where(self.table_efg.id == 1)

        q = Query.from_(self.table_abc).select("foo", "bar").select(subq.as_("sq"))

        self.assertEqual(
            'SELECT "foo","bar",(SELECT "fizzbuzz" FROM "efg" WHERE "id"=1) "sq" ' 'FROM "abc"',
            str(q),
        )

    def test_where__equality(self):
        subquery = Query.from_("efg").select("fiz").where(F("buz") == 0)
        query = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .where(self.table_abc.bar == subquery)
        )

        self.assertEqual(
            'SELECT "foo","bar" FROM "abc" ' 'WHERE "bar"=(SELECT "fiz" FROM "efg" WHERE "buz"=0)',
            str(query),
        )

    def test_select_from_nested_query(self):
        subquery = Query.from_(self.table_abc).select(
            self.table_abc.foo,
            self.table_abc.bar,
            (self.table_abc.fizz + self.table_abc.buzz).as_("fizzbuzz"),
        )

        query = Query.from_(subquery).select(subquery.foo, subquery.bar, subquery.fizzbuzz)

        self.assertEqual(
            'SELECT "sq0"."foo","sq0"."bar","sq0"."fizzbuzz" '
            "FROM ("
            'SELECT "foo","bar","fizz"+"buzz" "fizzbuzz" '
            'FROM "abc"'
            ') "sq0"',
            str(query),
        )

    def test_select_from_nested_query_with_join(self):
        subquery1 = (
            Query.from_(self.table_abc)
            .select(
                self.table_abc.foo,
                fn.Sum(self.table_abc.fizz + self.table_abc.buzz).as_("fizzbuzz"),
            )
            .groupby(self.table_abc.foo)
        )

        subquery2 = Query.from_(self.table_efg).select(
            self.table_efg.foo.as_("foo_two"),
            self.table_efg.bar,
        )

        query = (
            Query.from_(subquery1)
            .select(subquery1.foo, subquery1.fizzbuzz)
            .join(subquery2)
            .on(subquery1.foo == subquery2.foo_two)
            .select(subquery2.foo_two, subquery2.bar)
        )

        self.assertEqual(
            "SELECT "
            '"sq0"."foo","sq0"."fizzbuzz",'
            '"sq1"."foo_two","sq1"."bar" '
            "FROM ("
            "SELECT "
            '"foo",SUM("fizz"+"buzz") "fizzbuzz" '
            'FROM "abc" '
            'GROUP BY "foo"'
            ') "sq0" JOIN ('
            "SELECT "
            '"foo" "foo_two","bar" '
            'FROM "efg"'
            ') "sq1" ON "sq0"."foo"="sq1"."foo_two"',
            str(query),
        )

    def test_from_subquery_without_alias(self):
        subquery = Query.from_(self.table_efg).select(
            self.table_efg.base_id.as_("x"), self.table_efg.fizz, self.table_efg.buzz
        )

        test_query = Query.from_(subquery).select(subquery.x, subquery.fizz, subquery.buzz)

        self.assertEqual(
            'SELECT "sq0"."x","sq0"."fizz","sq0"."buzz" '
            "FROM ("
            'SELECT "base_id" "x","fizz","buzz" FROM "efg"'
            ') "sq0"',
            str(test_query),
        )

    def test_join_query_with_alias(self):
        subquery = (
            Query.from_(self.table_efg)
            .select(
                self.table_efg.base_id.as_("x"),
                self.table_efg.fizz,
                self.table_efg.buzz,
            )
            .as_("subq")
        )

        test_query = Query.from_(subquery).select(subquery.x, subquery.fizz, subquery.buzz)

        self.assertEqual(
            'SELECT "subq"."x","subq"."fizz","subq"."buzz" '
            "FROM ("
            'SELECT "base_id" "x","fizz","buzz" FROM "efg"'
            ') "subq"',
            str(test_query),
        )

    def test_with(self):
        sub_query = Query.from_(self.table_efg).select("fizz")
        test_query = Query.with_(sub_query, "an_alias").from_(AliasedQuery("an_alias")).select("*")

        self.assertEqual(
            'WITH an_alias AS (SELECT "fizz" FROM "efg") SELECT * FROM an_alias',
            str(test_query),
        )

    def test_with_more_than_one(self):
        s1 = Query.from_(self.table_efg).select("fizz")
        s2 = Query.from_("a1").select("foo")
        a1 = AliasedQuery("a1", s1)
        a2 = AliasedQuery("a2", s2)
        test_query = (
            Query.with_(s1, "a1").with_(s2, "a2").from_("a1").from_("a2").select(a1.fizz, a2.foo)
        )
        self.assertEqual(
            'WITH a1 AS (SELECT "fizz" FROM "efg") ,a2 AS (SELECT "foo" FROM "a1")'
            ' SELECT "a1"."fizz","a2"."foo" FROM "a1","a2"',
            str(test_query),
        )

    def test_with_recursive(self):
        sub_query = (
            Query.from_(self.table_efg).select("fizz").union(Query.from_("an_alias").select("fizz"))
        )
        test_query = Query.with_(sub_query, "an_alias").from_(AliasedQuery("an_alias")).select("*")

        self.assertEqual(
            'WITH RECURSIVE an_alias AS ((SELECT "fizz" FROM "efg")'
            ' UNION (SELECT "fizz" FROM "an_alias")) SELECT * FROM an_alias',
            str(test_query),
        )

    def test_with_column_recursive(self):
        sub_query = (
            Query.from_(self.table_efg).select("fizz").union(Query.from_("an_alias").select("fizz"))
        )
        test_query = (
            Query.with_(sub_query, "an_alias", Field("fizz"))
            .from_(AliasedQuery("an_alias"))
            .select("*")
        )

        self.assertEqual(
            'WITH RECURSIVE an_alias("fizz") AS ((SELECT "fizz" FROM "e'
            'fg") UNION (SELECT "fizz" FROM "an_alias")) SELECT * FROM an_alias',
            str(test_query),
        )

    def test_join_with_with(self):
        sub_query = Query.from_(self.table_efg).select("fizz")
        test_query = (
            Query.with_(sub_query, "an_alias")
            .from_(self.table_abc)
            .join(AliasedQuery("an_alias"))
            .on(AliasedQuery("an_alias").fizz == self.table_abc.buzz)
            .select("*")
        )
        self.assertEqual(
            'WITH an_alias AS (SELECT "fizz" FROM "efg") '
            'SELECT * FROM "abc" JOIN an_alias ON "an_alias"."fizz"="abc"."buzz"',
            str(test_query),
        )

    def test_select_from_with_returning(self):
        sub_query = PostgreSQLQuery.into(self.table_abc).insert(1).returning("*")
        test_query = Query.with_(sub_query, "an_alias").from_(AliasedQuery("an_alias")).select("*")
        self.assertEqual(
            'WITH an_alias AS (INSERT INTO "abc" VALUES (1) RETURNING *) SELECT * FROM an_alias',
            str(test_query),
        )


class QuoteTests(unittest.TestCase):
    def test_extraneous_quotes(self):
        t1 = Table("table1", alias="t1")
        t2 = Table("table2", alias="t2")

        query = Query.from_(t1).join(t2).on(t1.Value.between(t2.start, t2.end)).select(t1.value)

        self.assertEqual(
            "SELECT t1.value FROM table1 t1 "
            "JOIN table2 t2 ON t1.Value "
            "BETWEEN t2.start AND t2.end",
            query.get_sql(quote_char=None),
        )
