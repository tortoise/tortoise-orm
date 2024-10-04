import unittest

from pypika import Query, Rollup, RollupException, Table
from pypika import functions as fn

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"


class RollupTests(unittest.TestCase):
    table = Table("abc")

    def test_mysql_one_groupby(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, fn.Sum(self.table.bar))
            .rollup(self.table.foo, vendor="mysql")
        )

        self.assertEqual('SELECT "foo",SUM("bar") FROM "abc" GROUP BY "foo" WITH ROLLUP', str(q))

    def test_mysql_rollup_two_groupbys(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, self.table.fiz, fn.Sum(self.table.bar))
            .rollup(self.table.foo, self.table.fiz, vendor="mysql")
        )

        self.assertEqual(
            'SELECT "foo","fiz",SUM("bar") FROM "abc" GROUP BY "foo","fiz" WITH ROLLUP',
            str(q),
        )

    def test_no_rollup_before_groupby(self):
        with self.assertRaises(RollupException):
            Query.from_(self.table).select(self.table.foo, fn.Sum(self.table.bar)).rollup(
                vendor="mysql"
            )

    def test_no_rollup_after_rollup_mysql(self):
        with self.assertRaises(AttributeError):
            Query.from_(self.table).select(
                self.table.foo, self.table.fiz, fn.Sum(self.table.bar)
            ).rollup(self.table.foo, vendor="mysql").rollup(self.table.fiz, vendor="mysql")

    def test_verticaoracle_func_one_groupby(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, fn.Sum(self.table.bar))
            .groupby(Rollup(self.table.foo))
        )

        self.assertEqual('SELECT "foo",SUM("bar") FROM "abc" GROUP BY ROLLUP("foo")', str(q))

    def test_verticaoracle_func_two_groupbys(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, self.table.fiz, fn.Sum(self.table.bar))
            .groupby(
                Rollup(
                    self.table.foo,
                    self.table.fiz,
                )
            )
        )

        self.assertEqual(
            'SELECT "foo","fiz",SUM("bar") FROM "abc" GROUP BY ROLLUP("foo","fiz")',
            str(q),
        )

    def test_verticaoracle_func_partial(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, self.table.fiz, self.table.buz, fn.Sum(self.table.bar))
            .groupby(
                Rollup(
                    self.table.foo,
                    self.table.fiz,
                ),
                self.table.buz,
            )
        )

        self.assertEqual(
            'SELECT "foo","fiz","buz",SUM("bar") FROM "abc" GROUP BY ROLLUP("foo","fiz"),"buz"',
            str(q),
        )

    def test_verticaoracle_from_groupbys(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, fn.Sum(self.table.bar))
            .rollup(self.table.foo)
        )

        self.assertEqual('SELECT "foo",SUM("bar") FROM "abc" GROUP BY ROLLUP("foo")', str(q))

    def test_verticaoracle_from_two_groupbys(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, self.table.fiz, fn.Sum(self.table.bar))
            .rollup(
                self.table.foo,
                self.table.fiz,
            )
        )

        self.assertEqual(
            'SELECT "foo","fiz",SUM("bar") FROM "abc" GROUP BY ROLLUP("foo","fiz")',
            str(q),
        )

    def test_verticaoracle_from_parameters(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, self.table.fiz, fn.Sum(self.table.bar))
            .groupby(
                self.table.foo,
            )
            .rollup(
                self.table.fiz,
            )
        )

        self.assertEqual(
            'SELECT "foo","fiz",SUM("bar") FROM "abc" GROUP BY "foo",ROLLUP("fiz")',
            str(q),
        )

    def test_verticaoracle_multiple_rollups(self):
        q = (
            Query.from_(self.table)
            .select(self.table.foo, self.table.fiz, fn.Sum(self.table.bar))
            .rollup(
                self.table.foo,
            )
            .rollup(
                self.table.fiz,
            )
        )

        self.assertEqual(
            'SELECT "foo","fiz",SUM("bar") FROM "abc" GROUP BY ROLLUP("foo","fiz")',
            str(q),
        )

    def test_verticaoracle_rollups_with_parity(self):
        q = (
            Query.from_(self.table)
            .select(
                self.table.buz,
            )
            .rollup(
                [self.table.foo, self.table.bar],
                self.table.fiz,
            )
        )

        self.assertEqual('SELECT "buz" FROM "abc" GROUP BY ROLLUP(("foo","bar"),"fiz")', str(q))

    def test_verticaoracle_rollups_with_multiple_rollups_and_parity(self):
        q = (
            Query.from_(self.table)
            .select(
                self.table.buz,
            )
            .rollup(
                [self.table.foo, self.table.bar],
            )
            .rollup(
                [self.table.fiz, self.table.buz],
            )
        )

        self.assertEqual(
            'SELECT "buz" FROM "abc" GROUP BY ROLLUP(("foo","bar"),("fiz","buz"))',
            str(q),
        )
