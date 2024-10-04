import unittest

from pypika import Query, Tables
from pypika import functions as fn


class QuoteTests(unittest.TestCase):
    maxDiff = None

    table_abc, table_efg = Tables("abc", "efg")

    def setUp(self):
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

        self.query = (
            Query.from_(subquery1)
            .select(subquery1.foo, subquery1.fizzbuzz)
            .join(subquery2)
            .on(subquery1.foo == subquery2.foo_two)
            .select(subquery2.foo_two, subquery2.bar)
        )

    def test_replace_quote_char_in_complex_query(self):
        self.assertEqual(
            "SELECT "
            "`sq0`.`foo`,`sq0`.`fizzbuzz`,"
            "`sq1`.`foo_two`,`sq1`.`bar` "
            "FROM ("
            "SELECT "
            "`foo`,SUM(`fizz`+`buzz`) `fizzbuzz` "
            "FROM `abc` "
            "GROUP BY `foo`"
            ") `sq0` JOIN ("
            "SELECT "
            "`foo` `foo_two`,`bar` "
            "FROM `efg`"
            ") `sq1` ON `sq0`.`foo`=`sq1`.`foo_two`",
            self.query.get_sql(quote_char="`"),
        )

    def test_no_quote_char_in_complex_query(self):
        self.assertEqual(
            "SELECT "
            "sq0.foo,sq0.fizzbuzz,"
            "sq1.foo_two,sq1.bar "
            "FROM ("
            "SELECT "
            "foo,SUM(fizz+buzz) fizzbuzz "
            "FROM abc "
            "GROUP BY foo"
            ") sq0 JOIN ("
            "SELECT "
            "foo foo_two,bar "
            "FROM efg"
            ") sq1 ON sq0.foo=sq1.foo_two",
            self.query.get_sql(quote_char=None),
        )
