import unittest
from datetime import date, datetime

from pypika import Criterion, EmptyCriterion, Field, Table
from pypika import functions as fn
from pypika.queries import QueryBuilder
from pypika.terms import Mod

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"


class CriterionTests(unittest.TestCase):
    t = Table("test", alias="crit")

    def test__criterion_with_alias(self):
        c1 = (Field("foo") == Field("bar")).as_("criterion")

        self.assertEqual('"foo"="bar"', str(c1))
        self.assertEqual(
            '"foo"="bar" "criterion"',
            c1.get_sql(with_alias=True, quote_char='"', alias_quote_char='"'),
        )

    def test__criterion_eq_number(self):
        c1 = Field("foo") == 1
        c2 = Field("foo", table=self.t).eq(0)
        c3 = Field("foo", table=self.t) == -1

        self.assertEqual('"foo"=1', str(c1))
        self.assertEqual('"crit"."foo"=0', str(c2))
        self.assertEqual('"crit"."foo"=-1', str(c3))

    def test__criterion_eq_decimal(self):
        c1 = Field("foo") == 1.0
        c2 = Field("foo", table=self.t).eq(0.5)

        self.assertEqual('"foo"=1.0', str(c1))
        self.assertEqual('"crit"."foo"=0.5', str(c2))

    def test__criterion_eq_bool(self):
        c1 = Field("foo") == True  # noqa: E712
        c2 = Field("foo", table=self.t).eq(True)
        c3 = Field("foo") == False  # noqa: E712
        c4 = Field("foo", table=self.t).eq(False)

        self.assertEqual('"foo"=true', str(c1))
        self.assertEqual('"crit"."foo"=true', str(c2))
        self.assertEqual('"foo"=false', str(c3))
        self.assertEqual('"crit"."foo"=false', str(c4))

    def test__criterion_eq_str(self):
        c1 = Field("foo") == "abc"
        c2 = Field("foo", table=self.t).eq("abc")

        self.assertEqual("\"foo\"='abc'", str(c1))
        self.assertEqual('"crit"."foo"=\'abc\'', str(c2))

    def test__criterion_eq_date(self):
        c1 = Field("foo") == date(2000, 1, 1)
        c2 = Field("foo", table=self.t).eq(date(2000, 1, 1))

        self.assertEqual("\"foo\"='2000-01-01'", str(c1))
        self.assertEqual('"crit"."foo"=\'2000-01-01\'', str(c2))

    def test__criterion_eq_datetime(self):
        c1 = Field("foo") == datetime(2000, 1, 1, 12, 30, 55)
        c2 = Field("foo", table=self.t).eq(datetime(2000, 1, 1, 12, 30, 55))

        self.assertEqual("\"foo\"='2000-01-01T12:30:55'", str(c1))
        self.assertEqual('"crit"."foo"=\'2000-01-01T12:30:55\'', str(c2))

    def test__criterion_eq_right(self):
        c1 = 1 == Field("foo")
        c2 = -1 == Field("foo", table=self.t)

        self.assertEqual('"foo"=1', str(c1))
        self.assertEqual('"crit"."foo"=-1', str(c2))

    def test__criterion_is_null(self):
        c1 = Field("foo").isnull()
        c2 = Field("foo", table=self.t).isnull()

        self.assertEqual('"foo" IS NULL', str(c1))
        self.assertEqual('"crit"."foo" IS NULL', str(c2))

    def test__criterion_is_null_with_alias(self):
        c1 = Field("foo").isnull().as_("alias")
        c2 = Field("foo", table=self.t).isnull().as_("alias")

        self.assertEqual('"foo" IS NULL "alias"', str(c1))
        self.assertEqual('"crit"."foo" IS NULL "alias"', str(c2))

    def test__criterion_ne_number(self):
        c1 = Field("foo") != 1
        c2 = Field("foo", table=self.t).ne(0)
        c3 = Field("foo") != -1

        self.assertEqual('"foo"<>1', str(c1))
        self.assertEqual('"crit"."foo"<>0', str(c2))
        self.assertEqual('"foo"<>-1', str(c3))

    def test__criterion_ne_str(self):
        c1 = Field("foo") != "abc"
        c2 = Field("foo", table=self.t).ne("abc")

        self.assertEqual("\"foo\"<>'abc'", str(c1))
        self.assertEqual('"crit"."foo"<>\'abc\'', str(c2))

    def test__criterion_ne_date(self):
        c1 = Field("foo") != date(2000, 1, 1)
        c2 = Field("foo", table=self.t).ne(date(2000, 1, 1))

        self.assertEqual("\"foo\"<>'2000-01-01'", str(c1))
        self.assertEqual('"crit"."foo"<>\'2000-01-01\'', str(c2))

    def test__criterion_ne_datetime(self):
        c1 = Field("foo") != datetime(2000, 1, 1, 12, 30, 55)
        c2 = Field("foo", table=self.t).ne(datetime(2000, 1, 1, 12, 30, 55))

        self.assertEqual("\"foo\"<>'2000-01-01T12:30:55'", str(c1))
        self.assertEqual('"crit"."foo"<>\'2000-01-01T12:30:55\'', str(c2))

    def test__criterion_ne_right(self):
        c1 = 1 != Field("foo")
        c2 = -1 != Field("foo", table=self.t)

        self.assertEqual('"foo"<>1', str(c1))
        self.assertEqual('"crit"."foo"<>-1', str(c2))

    def test__criterion_lt_number(self):
        c1 = Field("foo") < 1
        c2 = Field("foo", table=self.t).lt(0)
        c3 = Field("foo") < -1

        self.assertEqual('"foo"<1', str(c1))
        self.assertEqual('"crit"."foo"<0', str(c2))
        self.assertEqual('"foo"<-1', str(c3))

    def test__criterion_lt_date(self):
        c1 = Field("foo") < date(2000, 1, 1)
        c2 = Field("foo", table=self.t).lt(date(2000, 1, 1))

        self.assertEqual("\"foo\"<'2000-01-01'", str(c1))
        self.assertEqual('"crit"."foo"<\'2000-01-01\'', str(c2))

    def test__criterion_lt_datetime(self):
        c1 = Field("foo") < datetime(2000, 1, 1, 12, 30, 55)
        c2 = Field("foo", table=self.t).lt(datetime(2000, 1, 1, 12, 30, 55))

        self.assertEqual("\"foo\"<'2000-01-01T12:30:55'", str(c1))
        self.assertEqual('"crit"."foo"<\'2000-01-01T12:30:55\'', str(c2))

    def test__criterion_lt_right(self):
        c1 = 1 > Field("foo")
        c2 = -1 > Field("foo", table=self.t)

        self.assertEqual('"foo"<1', str(c1))
        self.assertEqual('"crit"."foo"<-1', str(c2))

    def test__criterion_gt_number(self):
        c1 = Field("foo") > 1
        c2 = Field("foo", table=self.t).gt(0)
        c3 = Field("foo") > -1

        self.assertEqual('"foo">1', str(c1))
        self.assertEqual('"crit"."foo">0', str(c2))
        self.assertEqual('"foo">-1', str(c3))

    def test__criterion_gt_date(self):
        c1 = Field("foo") > date(2000, 1, 1)
        c2 = Field("foo", table=self.t).gt(date(2000, 1, 1))

        self.assertEqual("\"foo\">'2000-01-01'", str(c1))
        self.assertEqual('"crit"."foo">\'2000-01-01\'', str(c2))

    def test__criterion_gt_datetime(self):
        c1 = Field("foo") > datetime(2000, 1, 1, 12, 30, 55)
        c2 = Field("foo", table=self.t).gt(datetime(2000, 1, 1, 12, 30, 55))

        self.assertEqual("\"foo\">'2000-01-01T12:30:55'", str(c1))
        self.assertEqual('"crit"."foo">\'2000-01-01T12:30:55\'', str(c2))

    def test__criterion_gt_right(self):
        c1 = 1 < Field("foo")
        c2 = -1 < Field("foo", table=self.t)

        self.assertEqual('"foo">1', str(c1))
        self.assertEqual('"crit"."foo">-1', str(c2))

    def test__criterion_lte_number(self):
        c1 = Field("foo") <= 1
        c2 = Field("foo", table=self.t).lte(0)
        c3 = Field("foo") <= -1

        self.assertEqual('"foo"<=1', str(c1))
        self.assertEqual('"crit"."foo"<=0', str(c2))
        self.assertEqual('"foo"<=-1', str(c3))

    def test__criterion_lte_date(self):
        c1 = Field("foo") <= date(2000, 1, 1)
        c2 = Field("foo", table=self.t).lte(date(2000, 1, 1))

        self.assertEqual("\"foo\"<='2000-01-01'", str(c1))
        self.assertEqual('"crit"."foo"<=\'2000-01-01\'', str(c2))

    def test__criterion_lte_datetime(self):
        c1 = Field("foo") <= datetime(2000, 1, 1, 12, 30, 55)
        c2 = Field("foo", table=self.t).lte(datetime(2000, 1, 1, 12, 30, 55))

        self.assertEqual("\"foo\"<='2000-01-01T12:30:55'", str(c1))
        self.assertEqual('"crit"."foo"<=\'2000-01-01T12:30:55\'', str(c2))

    def test__criterion_lte_right(self):
        c1 = 1 >= Field("foo")
        c2 = -1 >= Field("foo", table=self.t)

        self.assertEqual('"foo"<=1', str(c1))
        self.assertEqual('"crit"."foo"<=-1', str(c2))

    def test__criterion_gte_number(self):
        c1 = Field("foo") >= 1
        c2 = Field("foo", table=self.t).gte(0)
        c3 = Field("foo") >= -1

        self.assertEqual('"foo">=1', str(c1))
        self.assertEqual('"crit"."foo">=0', str(c2))
        self.assertEqual('"foo">=-1', str(c3))

    def test__criterion_gte_date(self):
        c1 = Field("foo") >= date(2000, 1, 1)
        c2 = Field("foo", table=self.t).gte(date(2000, 1, 1))

        self.assertEqual("\"foo\">='2000-01-01'", str(c1))
        self.assertEqual('"crit"."foo">=\'2000-01-01\'', str(c2))

    def test__criterion_gte_datetime(self):
        c1 = Field("foo") >= datetime(2000, 1, 1, 12, 30, 55)
        c2 = Field("foo", table=self.t).gte(datetime(2000, 1, 1, 12, 30, 55))

        self.assertEqual("\"foo\">='2000-01-01T12:30:55'", str(c1))
        self.assertEqual('"crit"."foo">=\'2000-01-01T12:30:55\'', str(c2))

    def test__criterion_gte_right(self):
        c1 = 1 <= Field("foo")
        c2 = -1 <= Field("foo", table=self.t)

        self.assertEqual('"foo">=1', str(c1))
        self.assertEqual('"crit"."foo">=-1', str(c2))

    def test__criterion_bitwise_and(self):
        c1 = Field("foo").bitwiseand(2)
        c2 = Field("foo", table=self.t).bitwiseand(10) == 2

        self.assertEqual('("foo" & 2)', str(c1))
        self.assertEqual('("crit"."foo" & 10)=2', str(c2))

    def test__criterion_bitwise_and_with_alias(self):
        c1 = Field("foo").bitwiseand(2).as_("alias")

        self.assertEqual('("foo" & 2) "alias"', str(c1))

    def test__bitwise_and_in_where_clause(self):
        q = QueryBuilder().from_("items").select("abc").where(Field("foo").bitwiseand(1) == 1)

        self.assertEqual('SELECT "abc" FROM "items" WHERE ("foo" & 1)=1', str(q))


class NotTests(unittest.TestCase):
    table_abc, table_efg = Table("abc", alias="cx0"), Table("efg", alias="cx1")

    def test_negate(self):
        c1 = Field("foo") >= 1
        c2 = c1.negate()

        self.assertEqual('"foo">=1', str(c1))
        self.assertEqual('NOT "foo">=1', str(c2))

    def test_variable_access(self):
        c1 = Field("foo").negate()

        self.assertEqual(c1.is_aggregate, False)

    def test_chained_function(self):
        field1 = Field("foo").negate()
        field2 = field1.eq("bar")

        self.assertEqual('NOT "foo"', str(field1))
        self.assertEqual("NOT \"foo\"='bar'", str(field2))
        self.assertIsNot(field1, field2)

    def test_not_null(self):
        c1 = Field("foo").notnull()
        c2 = Field("foo", table=self.table_abc).notnull()

        self.assertEqual('NOT "foo" IS NULL', str(c1))
        self.assertEqual('NOT "cx0"."foo" IS NULL', str(c2))

    def test_not_null_with_alias(self):
        c1 = Field("foo").notnull().as_("something")
        c2 = Field("foo", table=self.table_abc).notnull().as_("something")

        self.assertEqual('NOT "foo" IS NULL "something"', str(c1))
        self.assertEqual('NOT "cx0"."foo" IS NULL "something"', str(c2))

    def test_notnullcriterion_replace_table(self):
        f = self.table_abc.foo.notnull().replace_table(self.table_abc, self.table_efg)

        self.assertEqual('NOT "cx1"."foo" IS NULL', str(f))

    def test_not_with_or_criterion(self):
        self.assertEqual('NOT ("foo" OR "bar")', str(~(Field("foo") | Field("bar"))))

    def test_not_with_and_criterion(self):
        self.assertEqual('NOT ("foo" AND "bar")', str(~(Field("foo") & Field("bar"))))

    def test_not_with_complex_criterion(self):
        self.assertEqual(
            'NOT ("foo" AND "bar" AND "fizz" AND "buzz")',
            str(~(Field("foo") & Field("bar") & Field("fizz") & Field("buzz"))),
        )


class BetweenTests(unittest.TestCase):
    t = Table("abc", alias="btw")

    def test__between_number(self):
        c1 = Field("foo").between(0, 1)
        c2 = Field("foo", table=self.t).between(0, 1)
        c3 = Field("foo")[0:1]

        self.assertEqual('"foo" BETWEEN 0 AND 1', str(c1))
        self.assertEqual('"btw"."foo" BETWEEN 0 AND 1', str(c2))
        self.assertEqual('"foo" BETWEEN 0 AND 1', str(c3))

    def test__between_with_alias(self):
        c1 = Field("foo").between(0, 1).as_("alias")
        c2 = Field("foo", table=self.t).between(0, 1).as_("alias")
        c3 = Field("foo")[0:1].as_("alias")

        self.assertEqual('"foo" BETWEEN 0 AND 1 "alias"', str(c1))
        self.assertEqual('"btw"."foo" BETWEEN 0 AND 1 "alias"', str(c2))
        self.assertEqual('"foo" BETWEEN 0 AND 1 "alias"', str(c3))

    def test__between_date(self):
        c1 = Field("foo").between(date(2000, 1, 1), date(2000, 12, 31))
        c2 = Field("foo", table=self.t).between(date(2000, 1, 1), date(2000, 12, 31))
        c3 = Field("foo")[date(2000, 1, 1) : date(2000, 12, 31)]

        self.assertEqual("\"foo\" BETWEEN '2000-01-01' AND '2000-12-31'", str(c1))
        self.assertEqual("\"btw\".\"foo\" BETWEEN '2000-01-01' AND '2000-12-31'", str(c2))
        self.assertEqual("\"foo\" BETWEEN '2000-01-01' AND '2000-12-31'", str(c3))

    def test__between_datetime(self):
        c1 = Field("foo").between(datetime(2000, 1, 1, 0, 0, 0), datetime(2000, 12, 31, 23, 59, 59))
        c2 = Field("foo", table=self.t).between(
            datetime(2000, 1, 1, 0, 0, 0), datetime(2000, 12, 31, 23, 59, 59)
        )
        c3 = Field("foo")[datetime(2000, 1, 1, 0, 0, 0) : datetime(2000, 12, 31, 23, 59, 59)]

        self.assertEqual("\"foo\" BETWEEN '2000-01-01T00:00:00' AND '2000-12-31T23:59:59'", str(c1))
        self.assertEqual(
            "\"btw\".\"foo\" BETWEEN '2000-01-01T00:00:00' AND '2000-12-31T23:59:59'",
            str(c2),
        )
        self.assertEqual("\"foo\" BETWEEN '2000-01-01T00:00:00' AND '2000-12-31T23:59:59'", str(c3))

    def test__function_between(self):
        c1 = fn.Coalesce(Field("foo"), 0)[0:1]
        c2 = fn.Coalesce(Field("foo", table=self.t), 0)[0:1]

        self.assertEqual('COALESCE("foo",0) BETWEEN 0 AND 1', str(c1))
        self.assertEqual('COALESCE("btw"."foo",0) BETWEEN 0 AND 1', str(c2))

    def test_get_item_only_works_with_slice(self):
        with self.assertRaises(TypeError):
            Field("foo")[0]

        with self.assertRaises(TypeError):
            Field("foo")[date(2000, 1, 1)]

        with self.assertRaises(TypeError):
            Field("foo")[datetime(2000, 1, 1, 0, 0, 0)]


class IsInTests(unittest.TestCase):
    t = Table("abc", alias="isin")

    def test__in_number(self):
        c1 = Field("foo").isin([0, 1])
        c2 = Field("foo", table=self.t).isin([0, 1])

        self.assertEqual('"foo" IN (0,1)', str(c1))
        self.assertEqual('"isin"."foo" IN (0,1)', str(c2))

    def test__in_number_with_alias(self):
        c1 = Field("foo").isin([0, 1]).as_("alias")
        c2 = Field("foo", table=self.t).isin([0, 1]).as_("alias")

        self.assertEqual('"foo" IN (0,1) "alias"', str(c1))
        self.assertEqual('"isin"."foo" IN (0,1) "alias"', str(c2))

    def test__in_character(self):
        c1 = Field("foo").isin(["a", "b"])
        c2 = Field("foo", table=self.t).isin(["a", "b"])

        self.assertEqual("\"foo\" IN ('a','b')", str(c1))
        self.assertEqual("\"isin\".\"foo\" IN ('a','b')", str(c2))

    def test__in_date(self):
        c1 = Field("foo").isin([date(2000, 1, 1), date(2000, 12, 31)])
        c2 = Field("foo", table=self.t).isin([date(2000, 1, 1), date(2000, 12, 31)])

        self.assertEqual("\"foo\" IN ('2000-01-01','2000-12-31')", str(c1))
        self.assertEqual("\"isin\".\"foo\" IN ('2000-01-01','2000-12-31')", str(c2))

    def test__in_datetime(self):
        c1 = Field("foo").isin([datetime(2000, 1, 1, 0, 0, 0), datetime(2000, 12, 31, 23, 59, 59)])
        c2 = Field("foo", table=self.t).isin(
            [datetime(2000, 1, 1, 0, 0, 0), datetime(2000, 12, 31, 23, 59, 59)]
        )

        self.assertEqual("\"foo\" IN ('2000-01-01T00:00:00','2000-12-31T23:59:59')", str(c1))
        self.assertEqual(
            "\"isin\".\"foo\" IN ('2000-01-01T00:00:00','2000-12-31T23:59:59')", str(c2)
        )

    def test__function_isin(self):
        c1 = fn.Coalesce(Field("foo"), 0).isin([0, 1])
        c2 = fn.Coalesce(Field("foo", table=self.t), 0).isin([0, 1])

        self.assertEqual('COALESCE("foo",0) IN (0,1)', str(c1))
        self.assertEqual('COALESCE("isin"."foo",0) IN (0,1)', str(c2))

    def test__in_unicode(self):
        c1 = Field("foo").isin(["a", "b"])
        c2 = Field("foo", table=self.t).isin(["a", "b"])

        self.assertEqual("\"foo\" IN ('a','b')", str(c1))
        self.assertEqual("\"isin\".\"foo\" IN ('a','b')", str(c2))


class NotInTests(unittest.TestCase):
    t = Table("abc", alias="notin")

    def test__notin_number(self):
        c1 = Field("foo").notin([0, 1])
        c2 = Field("foo", table=self.t).notin([0, 1])

        self.assertEqual('"foo" NOT IN (0,1)', str(c1))
        self.assertEqual('"notin"."foo" NOT IN (0,1)', str(c2))

    def test__notin_number_with_alias(self):
        c1 = Field("foo").notin([0, 1]).as_("alias")
        c2 = Field("foo", table=self.t).notin([0, 1]).as_("alias")

        self.assertEqual('"foo" NOT IN (0,1) "alias"', str(c1))
        self.assertEqual('"notin"."foo" NOT IN (0,1) "alias"', str(c2))

    def test__notin_character(self):
        c1 = Field("foo").notin(["a", "b"])
        c2 = Field("foo", table=self.t).notin(["a", "b"])

        self.assertEqual("\"foo\" NOT IN ('a','b')", str(c1))
        self.assertEqual("\"notin\".\"foo\" NOT IN ('a','b')", str(c2))

    def test__notin_date(self):
        c1 = Field("foo").notin([date(2000, 1, 1), date(2000, 12, 31)])
        c2 = Field("foo", table=self.t).notin([date(2000, 1, 1), date(2000, 12, 31)])

        self.assertEqual("\"foo\" NOT IN ('2000-01-01','2000-12-31')", str(c1))
        self.assertEqual("\"notin\".\"foo\" NOT IN ('2000-01-01','2000-12-31')", str(c2))

    def test__notin_datetime(self):
        c1 = Field("foo").notin([datetime(2000, 1, 1, 0, 0, 0), datetime(2000, 12, 31, 23, 59, 59)])
        c2 = Field("foo", table=self.t).notin(
            [datetime(2000, 1, 1, 0, 0, 0), datetime(2000, 12, 31, 23, 59, 59)]
        )

        self.assertEqual("\"foo\" NOT IN ('2000-01-01T00:00:00','2000-12-31T23:59:59')", str(c1))
        self.assertEqual(
            "\"notin\".\"foo\" NOT IN ('2000-01-01T00:00:00','2000-12-31T23:59:59')",
            str(c2),
        )

    def test__function_notin(self):
        c1 = fn.Coalesce(Field("foo"), 0).notin([0, 1])
        c2 = fn.Coalesce(Field("foo", table=self.t), 0).notin([0, 1])

        self.assertEqual('COALESCE("foo",0) NOT IN (0,1)', str(c1))
        self.assertEqual('COALESCE("notin"."foo",0) NOT IN (0,1)', str(c2))


class LikeTests(unittest.TestCase):
    t = Table("abc", alias="like")

    def test_like_starts_with(self):
        c1 = Field("foo").like("ab%")
        c2 = Field("foo", table=self.t).like("ab%")

        self.assertEqual("\"foo\" LIKE 'ab%'", str(c1))
        self.assertEqual('"like"."foo" LIKE \'ab%\'', str(c2))

    def test_like_contains(self):
        c1 = Field("foo").like("%ab%")
        c2 = Field("foo", table=self.t).like("%ab%")

        self.assertEqual("\"foo\" LIKE '%ab%'", str(c1))
        self.assertEqual('"like"."foo" LIKE \'%ab%\'', str(c2))

    def test_like_ends_with(self):
        c1 = Field("foo").like("%ab")
        c2 = Field("foo", table=self.t).like("%ab")

        self.assertEqual("\"foo\" LIKE '%ab'", str(c1))
        self.assertEqual('"like"."foo" LIKE \'%ab\'', str(c2))

    def test_like_n_chars_long(self):
        c1 = Field("foo").like("___")
        c2 = Field("foo", table=self.t).like("___")

        self.assertEqual("\"foo\" LIKE '___'", str(c1))
        self.assertEqual('"like"."foo" LIKE \'___\'', str(c2))

    def test_like_single_chars_and_various_chars(self):
        c1 = Field("foo").like("a_b%c")
        c2 = Field("foo", table=self.t).like("a_b%c")

        self.assertEqual("\"foo\" LIKE 'a_b%c'", str(c1))
        self.assertEqual('"like"."foo" LIKE \'a_b%c\'', str(c2))

    def test_not_like_single_chars_and_various_chars(self):
        c1 = Field("foo").not_like("a_b%c")
        c2 = Field("foo", table=self.t).not_like("a_b%c")

        self.assertEqual("\"foo\" NOT LIKE 'a_b%c'", str(c1))
        self.assertEqual('"like"."foo" NOT LIKE \'a_b%c\'', str(c2))

    def test_ilike_starts_with(self):
        c1 = Field("foo").ilike("ab%")
        c2 = Field("foo", table=self.t).ilike("ab%")

        self.assertEqual("\"foo\" ILIKE 'ab%'", str(c1))
        self.assertEqual('"like"."foo" ILIKE \'ab%\'', str(c2))

    def test_ilike_contains(self):
        c1 = Field("foo").ilike("%ab%")
        c2 = Field("foo", table=self.t).ilike("%ab%")

        self.assertEqual("\"foo\" ILIKE '%ab%'", str(c1))
        self.assertEqual('"like"."foo" ILIKE \'%ab%\'', str(c2))

    def test_ilike_ends_with(self):
        c1 = Field("foo").ilike("%ab")
        c2 = Field("foo", table=self.t).ilike("%ab")

        self.assertEqual("\"foo\" ILIKE '%ab'", str(c1))
        self.assertEqual('"like"."foo" ILIKE \'%ab\'', str(c2))

    def test_ilike_n_chars_long(self):
        c1 = Field("foo").ilike("___")
        c2 = Field("foo", table=self.t).ilike("___")

        self.assertEqual("\"foo\" ILIKE '___'", str(c1))
        self.assertEqual('"like"."foo" ILIKE \'___\'', str(c2))

    def test_ilike_single_chars_and_various_chars(self):
        c1 = Field("foo").ilike("a_b%c")
        c2 = Field("foo", table=self.t).ilike("a_b%c")

        self.assertEqual("\"foo\" ILIKE 'a_b%c'", str(c1))
        self.assertEqual('"like"."foo" ILIKE \'a_b%c\'', str(c2))

    def test_not_ilike_single_chars_and_various_chars(self):
        c1 = Field("foo").not_ilike("a_b%c")
        c2 = Field("foo", table=self.t).not_ilike("a_b%c")

        self.assertEqual("\"foo\" NOT ILIKE 'a_b%c'", str(c1))
        self.assertEqual('"like"."foo" NOT ILIKE \'a_b%c\'', str(c2))

    def test_rlike_escape_chars(self):
        c1 = Field("foo").rlike("\\\\d+$")
        c2 = Field("foo", table=self.t).rlike("\\\\d+$")

        self.assertEqual("\"foo\" RLIKE '\\\\d+$'", str(c1))
        self.assertEqual('"like"."foo" RLIKE \'\\\\d+$\'', str(c2))

    def test_glob_single_chars_and_various_chars(self):
        c1 = Field("foo").glob("a_b*")
        c2 = Field("foo", table=self.t).glob("a_b*")

        self.assertEqual("\"foo\" GLOB 'a_b*'", str(c1))
        self.assertEqual('"like"."foo" GLOB \'a_b*\'', str(c2))


class ComplexCriterionTests(unittest.TestCase):
    table_abc, table_efg = Table("abc", alias="cx0"), Table("efg", alias="cx1")

    def test_and(self):
        c1 = (Field("foo") == 1) & (Field("bar") == 2)
        c2 = (Field("foo", table=self.table_abc) == 1) & (Field("bar", table=self.table_efg) == 2)

        self.assertEqual('"foo"=1 AND "bar"=2', str(c1))
        self.assertEqual('"cx0"."foo"=1 AND "cx1"."bar"=2', str(c2))

    def test_or(self):
        c1 = (Field("foo") == 1) | (Field("bar") == 2)
        c2 = (Field("foo", table=self.table_abc) == 1) | (Field("bar", table=self.table_efg) == 2)

        self.assertEqual('"foo"=1 OR "bar"=2', str(c1))
        self.assertEqual('"cx0"."foo"=1 OR "cx1"."bar"=2', str(c2))

    def test_xor(self):
        c1 = (Field("foo") == 1) ^ (Field("bar") == 2)
        c2 = (Field("foo", table=self.table_abc) == 1) ^ (Field("bar", table=self.table_efg) == 2)

        self.assertEqual('"foo"=1 XOR "bar"=2', str(c1))
        self.assertEqual('"cx0"."foo"=1 XOR "cx1"."bar"=2', str(c2))

    def test_function_and(self):
        c1 = fn.IsNull(Field("foo")) & (Field("bar") == 2)

        self.assertEqual('ISNULL("foo") AND "bar"=2', str(c1))

    def test_function_or(self):
        c1 = fn.IsNull(Field("foo")) | (Field("bar") == 2)

        self.assertEqual('ISNULL("foo") OR "bar"=2', str(c1))

    def test_function_xor(self):
        c1 = fn.IsNull(Field("foo")) ^ (Field("bar") == 2)

        self.assertEqual('ISNULL("foo") XOR "bar"=2', str(c1))

    def test__nested__and(self):
        c = (Field("foo") == 1) & (Field("bar") == 2) & (Field("buz") == 3)

        self.assertEqual('"foo"=1 AND "bar"=2 AND "buz"=3', str(c))

    def test__nested__or(self):
        c = (Field("foo") == 1) | (Field("bar") == 2) | (Field("buz") == 3)

        self.assertEqual('"foo"=1 OR "bar"=2 OR "buz"=3', str(c))

    def test__nested__mixed(self):
        c = ((Field("foo") == 1) & (Field("bar") == 2)) | (Field("buz") == 3)

        self.assertEqual('("foo"=1 AND "bar"=2) OR "buz"=3', str(c))

    def test__between_and_isin(self):
        c = Field("foo").isin([1, 2, 3]) & Field("bar").between(0, 1)

        self.assertEqual('"foo" IN (1,2,3) AND "bar" BETWEEN 0 AND 1', str(c))

    def test__between_and_field(self):
        c1 = Field("foo").between(0, 1)
        c2 = Field("bool_field")

        self.assertEqual('"foo" BETWEEN 0 AND 1 AND "bool_field"', str(c1 & c2))
        self.assertEqual('"bool_field" AND "foo" BETWEEN 0 AND 1', str(c2 & c1))


class FieldsAsCriterionTests(unittest.TestCase):
    def test__field_and_field(self):
        c1 = Field("a")
        c2 = Field("b")

        self.assertEqual('"a" AND "b"', str(c1 & c2))

    def test__field_or_field(self):
        c1 = Field("a")
        c2 = Field("b")

        self.assertEqual('"a" OR "b"', str(c1 | c2))

    def test__field_xor_field(self):
        c1 = Field("a")
        c2 = Field("b")

        self.assertEqual('"a" XOR "b"', str(c1 ^ c2))


class CriterionOperationsTests(unittest.TestCase):
    table_abc, table_efg = Table("abc", alias="cx0"), Table("efg", alias="cx1")

    def test_field_replace_table(self):
        f = self.table_abc.foo.replace_table(self.table_abc, self.table_efg)

        self.assertEqual('"cx1"."foo"', str(f))

    def test_arithmeticfunction_replace_table(self):
        f = (self.table_abc.foo + self.table_abc.bar).replace_table(self.table_abc, self.table_efg)

        self.assertEqual('"cx1"."foo"+"cx1"."bar"', str(f))

    def test_criterion_replace_table(self):
        f = (self.table_abc.foo < self.table_abc.bar).replace_table(self.table_abc, self.table_efg)

        self.assertEqual('"cx1"."foo"<"cx1"."bar"', str(f))

    def test_complexcriterion_replace_table(self):
        f = (self.table_abc.foo < self.table_abc.bar) & (self.table_abc.fiz > self.table_abc.buz)
        f = f.replace_table(self.table_abc, self.table_efg)

        self.assertEqual('"cx1"."foo"<"cx1"."bar" AND "cx1"."fiz">"cx1"."buz"', str(f))

    def test_function_with_only_fields_replace_table(self):
        f = fn.Sum(self.table_abc.foo).replace_table(self.table_abc, self.table_efg)

        self.assertEqual('SUM("cx1"."foo")', str(f))

    def test_function_with_values_and_fields_replace_table(self):
        f = Mod(self.table_abc.foo, 2).replace_table(self.table_abc, self.table_efg)

        self.assertEqual('MOD("cx1"."foo",2)', str(f))

    def test_betweencriterion_replace_table(self):
        f = self.table_abc.foo[0:1].replace_table(self.table_abc, self.table_efg)

        self.assertEqual('"cx1"."foo" BETWEEN 0 AND 1', str(f))

    def test_nullcriterion_replace_table(self):
        f = self.table_abc.foo.isnull().replace_table(self.table_abc, self.table_efg)

        self.assertEqual('"cx1"."foo" IS NULL', str(f))


class AnyTests(unittest.TestCase):
    def test_zero_args_returns_empty_criterion(self):
        crit = Criterion.any()
        self.assertIsInstance(crit, EmptyCriterion)

    def test_single_arg_returns_self(self):
        f = Field("a")
        crit = Criterion.any([f])
        self.assertEqual(str(f), str(crit))

    def test_multiple_args_returned_in_chain_of_ors(self):
        crit = Criterion.any([Field("a"), Field("b"), Field("c"), Field("d")])
        self.assertEqual(str(crit), '"a" OR "b" OR "c" OR "d"')

    def test_with_generator(self):
        crit = Criterion.any(Field(letter) for letter in "abcd")
        self.assertEqual(str(crit), '"a" OR "b" OR "c" OR "d"')


class EmptyCriterionTests(unittest.TestCase):
    def test_fields_(self):
        empty_criterion = EmptyCriterion()

        self.assertEqual(len(empty_criterion.fields_()), 0)


class AllTests(unittest.TestCase):
    def test_zero_args_returns_empty_criterion(self):
        crit = Criterion.all()
        self.assertIsInstance(crit, EmptyCriterion)

    def test_single_arg_returns_self(self):
        f = Field("a")
        crit = Criterion.all([f])
        self.assertEqual(str(f), str(crit))

    def test_multiple_args_returned_in_chain_of_ors(self):
        crit = Criterion.all([Field("a"), Field("b"), Field("c"), Field("d")])
        self.assertEqual(str(crit), '"a" AND "b" AND "c" AND "d"')

    def test_with_generator(self):
        crit = Criterion.all(Field(letter) for letter in "abcd")
        self.assertEqual(str(crit), '"a" AND "b" AND "c" AND "d"')
