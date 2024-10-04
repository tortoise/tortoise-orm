import unittest

from pypika import Criterion, JoinType, Order, Query, Tables
from pypika import analytics as an
from pypika.analytics import Lag, Lead

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"


class RankTests(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_rank(self):
        expr = an.Rank().over(self.table_abc.foo).orderby(self.table_abc.date)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT " "RANK() " 'OVER(PARTITION BY "foo" ORDER BY "date") ' 'FROM "abc"',
            str(q),
        )

    def test_dense_rank(self):
        expr = an.DenseRank().over(self.table_abc.foo).orderby(self.table_abc.date)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT " "DENSE_RANK() " 'OVER(PARTITION BY "foo" ORDER BY "date") ' 'FROM "abc"',
            str(q),
        )

    def test_row_number(self):
        expr = an.RowNumber().over(self.table_abc.foo).orderby(self.table_abc.date)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT " "ROW_NUMBER() " 'OVER(PARTITION BY "foo" ORDER BY "date") ' 'FROM "abc"',
            str(q),
        )

    def test_rank_with_alias(self):
        expr = an.Rank().over(self.table_abc.foo).orderby(self.table_abc.date).as_("rank")

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT " "RANK() " 'OVER(PARTITION BY "foo" ORDER BY "date") "rank" ' 'FROM "abc"',
            str(q),
        )

    def test_multiple_partitions(self):
        expr = an.Rank().orderby(self.table_abc.date).over(self.table_abc.foo, self.table_abc.bar)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT " "RANK() " 'OVER(PARTITION BY "foo","bar" ORDER BY "date") ' 'FROM "abc"',
            str(q),
        )

    def test_ntile_no_partition_or_order_invalid_sql(self):
        expr = an.NTile(5)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual("SELECT " "NTILE(5) " 'FROM "abc"', str(q))

    def test_ntile_with_partition(self):
        expr = an.NTile(5).over(self.table_abc.foo)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual("SELECT " "NTILE(5) " 'OVER(PARTITION BY "foo") ' 'FROM "abc"', str(q))

    def test_ntile_with_order(self):
        expr = an.NTile(5).orderby(self.table_abc.date)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual("SELECT " "NTILE(5) " 'OVER(ORDER BY "date") ' 'FROM "abc"', str(q))

    def test_ntile_with_partition_and_order(self):
        expr = an.NTile(5).over(self.table_abc.foo).orderby(self.table_abc.date)

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT " "NTILE(5) " 'OVER(PARTITION BY "foo" ORDER BY "date") ' 'FROM "abc"',
            str(q),
        )

    def test_first_value(self):
        expr = (
            an.FirstValue(self.table_abc.fizz).over(self.table_abc.foo).orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'FIRST_VALUE("fizz") '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_first_value_ignore_nulls(self):
        expr = (
            an.FirstValue(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .ignore_nulls()
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'FIRST_VALUE("fizz" IGNORE NULLS) '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_first_value_ignore_nulls_first(self):
        expr = (
            an.FirstValue(self.table_abc.fizz)
            .ignore_nulls()
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'FIRST_VALUE("fizz" IGNORE NULLS) '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_first_value_multi_argument(self):
        expr = (
            an.FirstValue(self.table_abc.fizz, self.table_abc.buzz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'FIRST_VALUE("fizz","buzz") '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_last_value(self):
        expr = (
            an.LastValue(self.table_abc.fizz).over(self.table_abc.foo).orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz") '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_filter(self):
        expr = (
            an.LastValue(self.table_abc.fizz)
            .filter(Criterion.all([self.table_abc.bar == True]))  # noqa: E712
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz") '
            'FILTER(WHERE "bar"=true) '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_filter_quote_table_in_filter(self):
        expr = (
            an.LastValue(self.table_efg.fizz)
            .filter(self.table_efg.filed.eq("yes"))
            .over(self.table_efg.foo)
            .orderby(self.table_efg.date)
        )

        q = (
            Query.from_(self.table_abc)
            .inner_join(self.table_efg)
            .on(self.table_abc.id.eq(self.table_efg.id))
            .select(expr)
        )

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("efg"."fizz") '
            'FILTER(WHERE "efg"."filed"=\'yes\') '
            'OVER(PARTITION BY "efg"."foo" ORDER BY "efg"."date") '
            'FROM "abc" '
            'JOIN "efg" ON "abc"."id"="efg"."id"',
            str(q),
        )

    def test_orderby_asc(self):
        expr = (
            an.LastValue(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date, order=Order.asc)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz") '
            'OVER(PARTITION BY "foo" ORDER BY "date" ASC) '
            'FROM "abc"',
            str(q),
        )

    def test_orderby_desc(self):
        expr = (
            an.LastValue(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date, order=Order.desc)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz") '
            'OVER(PARTITION BY "foo" ORDER BY "date" DESC) '
            'FROM "abc"',
            str(q),
        )

    def test_last_value_multi_argument(self):
        expr = (
            an.LastValue(self.table_abc.fizz, self.table_abc.buzz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz","buzz") '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_last_value_ignore_nulls(self):
        expr = (
            an.LastValue(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .ignore_nulls()
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz" IGNORE NULLS) '
            'OVER(PARTITION BY "foo" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_median(self):
        expr = (
            an.Median(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'MEDIAN("fizz") '
            'OVER(PARTITION BY "foo","bar" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_avg(self):
        expr = (
            an.Avg(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT " 'AVG("fizz") ' 'OVER(PARTITION BY "foo","bar" ORDER BY "date") ' 'FROM "abc"',
            str(q),
        )

    def test_stddev(self):
        expr = (
            an.StdDev(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'STDDEV("fizz") '
            'OVER(PARTITION BY "foo","bar" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_stddev_pop(self):
        expr = (
            an.StdDevPop(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'STDDEV_POP("fizz") '
            'OVER(PARTITION BY "foo","bar" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_stddev_samp(self):
        expr = (
            an.StdDevSamp(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'STDDEV_SAMP("fizz") '
            'OVER(PARTITION BY "foo","bar" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_variance(self):
        expr = (
            an.Variance(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'VARIANCE("fizz") '
            'OVER(PARTITION BY "foo","bar" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_var_pop(self):
        expr = (
            an.VarPop(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'VAR_POP("fizz") '
            'OVER(PARTITION BY "foo","bar" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_var_samp(self):
        expr = (
            an.VarSamp(self.table_abc.fizz)
            .over(self.table_abc.foo, self.table_abc.bar)
            .orderby(self.table_abc.date)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'VAR_SAMP("fizz") '
            'OVER(PARTITION BY "foo","bar" ORDER BY "date") '
            'FROM "abc"',
            str(q),
        )

    def test_table_prefixes_used_in_analytic_functions(self):
        expr = an.Rank().over(self.table_abc.foo).orderby(self.table_efg.date)

        query = (
            Query.from_(self.table_abc)
            .join(self.table_efg, how=JoinType.left)
            .on(self.table_abc.foo == self.table_efg.bar)
            .select("*", expr)
        )

        self.assertEqual(
            'SELECT *,RANK() OVER(PARTITION BY "abc"."foo" ORDER BY "efg"."date") '
            'FROM "abc" LEFT JOIN "efg" ON "abc"."foo"="efg"."bar"',
            str(query),
        )

    def test_sum_rows_unbounded_preceeding(self):
        expr = (
            an.Sum(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .rows(an.Preceding())
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'SUM("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "ROWS UNBOUNDED PRECEDING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_max_rows_x_preceeding(self):
        expr = (
            an.Max(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .rows(an.Preceding(5))
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'MAX("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "ROWS 5 PRECEDING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_min_rows_current_row(self):
        expr = (
            an.Min(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .rows(an.CURRENT_ROW)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'MIN("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "ROWS CURRENT ROW"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_varpop_range_unbounded_preceeding(self):
        expr = (
            an.VarPop(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .range(an.Preceding())
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'VAR_POP("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "RANGE UNBOUNDED PRECEDING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_max_range_x_preceeding(self):
        expr = (
            an.Max(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .range(an.Preceding(5))
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'MAX("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "RANGE 5 PRECEDING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_min_range_current_row(self):
        expr = (
            an.Min(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .range(an.CURRENT_ROW)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'MIN("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "RANGE CURRENT ROW"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_variance_rows_between_unbounded_preceeding_unbounded_following(self):
        expr = (
            an.Variance(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .rows(an.Preceding(), an.Following())
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'VARIANCE("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_first_value_range_between_x_preceeding_unbounded_following(self):
        expr = (
            an.FirstValue(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .range(an.Preceding(3), an.Following())
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'FIRST_VALUE("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "RANGE BETWEEN 3 PRECEDING AND UNBOUNDED FOLLOWING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_varpop_rows_between_unbounded_preceeding_x_following(self):
        expr = (
            an.VarPop(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .rows(an.Preceding(), an.Following(6))
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'VAR_POP("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "ROWS BETWEEN UNBOUNDED PRECEDING AND 6 FOLLOWING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_count_range_between_unbounded_preceeding_current_row(self):
        expr = (
            an.Count(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .range(an.Preceding(), an.CURRENT_ROW)
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'COUNT("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_last_value_rows_between_current_row_unbounded_following(self):
        expr = (
            an.LastValue(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .rows(an.CURRENT_ROW, an.Following())
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz") '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_last_value_rows_between_current_row_unbounded_following_ignore_nulls(self):
        expr = (
            an.LastValue(self.table_abc.fizz)
            .over(self.table_abc.foo)
            .orderby(self.table_abc.date)
            .ignore_nulls()
            .rows(an.CURRENT_ROW, an.Following(8))
        )

        q = Query.from_(self.table_abc).select(expr)

        self.assertEqual(
            "SELECT "
            'LAST_VALUE("fizz" IGNORE NULLS) '
            "OVER("
            'PARTITION BY "foo" ORDER BY "date" '
            "ROWS BETWEEN CURRENT ROW AND 8 FOLLOWING"
            ") "
            'FROM "abc"',
            str(q),
        )

    def test_empty_over(self):
        query = Query.from_(self.table_abc).select(an.Sum(self.table_abc.fizz).over())

        self.assertEqual("SELECT " 'SUM("fizz") OVER() ' 'FROM "abc"', str(query))

    def test_rows_called_twice_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            an.Sum(self.table_abc.fizz).over(self.table_abc.foo).orderby(self.table_abc.date).rows(
                an.Preceding()
            ).rows(an.Preceding())

    def test_range_called_twice_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            an.Sum(self.table_abc.fizz).over(self.table_abc.foo).orderby(self.table_abc.date).range(
                an.Preceding()
            ).range(an.Preceding())

    def test_rows_then_range_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            an.Sum(self.table_abc.fizz).over(self.table_abc.foo).orderby(self.table_abc.date).rows(
                an.Preceding()
            ).range(an.Preceding())

    def test_range_then_rows_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            an.Sum(self.table_abc.fizz).over(self.table_abc.foo).orderby(self.table_abc.date).range(
                an.Preceding()
            ).rows(an.Preceding())

    def test_lag_generates_correct_sql(self):
        with self.subTest("without partition by"):
            q = Query.from_(self.table_abc).select(
                Lag(self.table_abc.date, 1, "2000-01-01").orderby(self.table_abc.date)
            )

            self.assertEqual(
                'SELECT LAG("date",1,\'2000-01-01\') OVER(ORDER BY "date") FROM "abc"', str(q)
            )

        with self.subTest("with partition by"):
            q = Query.from_(self.table_abc).select(
                Lag(self.table_abc.date, 1, "2000-01-01")
                .over(self.table_abc.foo)
                .orderby(self.table_abc.date)
            )

            self.assertEqual(
                'SELECT LAG("date",1,\'2000-01-01\') OVER(PARTITION BY "foo" ORDER BY "date") FROM "abc"',
                str(q),
            )

    def test_lead_generates_correct_sql(self):
        with self.subTest("without partition by"):
            q = Query.from_(self.table_abc).select(
                Lead(self.table_abc.date, 1, "2000-01-01").orderby(self.table_abc.date)
            )

            self.assertEqual(
                'SELECT LEAD("date",1,\'2000-01-01\') OVER(ORDER BY "date") FROM "abc"', str(q)
            )

        with self.subTest("with partition by"):
            q = Query.from_(self.table_abc).select(
                Lead(self.table_abc.date, 1, "2000-01-01")
                .over(self.table_abc.foo)
                .orderby(self.table_abc.date)
            )

            self.assertEqual(
                'SELECT LEAD("date",1,\'2000-01-01\') OVER(PARTITION BY "foo" ORDER BY "date") FROM "abc"',
                str(q),
            )
