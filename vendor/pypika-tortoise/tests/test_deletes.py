import unittest

from pypika import SYSTEM_TIME, MySQLQuery, PostgreSQLQuery, Query, SQLLiteQuery, Table

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"

from pypika.terms import Star


class DeleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.table_abc = Table("abc")

    def test_omit_where(self):
        q = Query.from_("abc").delete()

        self.assertEqual('DELETE FROM "abc"', str(q))

    def test_omit_where__table_schema(self):
        q = Query.from_(Table("abc", "schema1")).delete()

        self.assertEqual('DELETE FROM "schema1"."abc"', str(q))

    def test_where_field_equals(self):
        q1 = Query.from_(self.table_abc).where(self.table_abc.foo == self.table_abc.bar).delete()
        q2 = Query.from_(self.table_abc).where(self.table_abc.foo.eq(self.table_abc.bar)).delete()

        self.assertEqual('DELETE FROM "abc" WHERE "foo"="bar"', str(q1))
        self.assertEqual('DELETE FROM "abc" WHERE "foo"="bar"', str(q2))

    def test_for_portion(self):
        with self.subTest("with system time"):
            q = Query.from_(
                self.table_abc.for_portion(SYSTEM_TIME.from_to("2020-01-01", "2020-02-01"))
            ).delete()

            self.assertEqual(
                "DELETE FROM \"abc\" FOR PORTION OF SYSTEM_TIME FROM '2020-01-01' TO '2020-02-01'",
                str(q),
            )

        with self.subTest("with column"):
            q = Query.from_(
                self.table_abc.for_portion(
                    self.table_abc.valid_period.from_to("2020-01-01", "2020-02-01")
                )
            ).delete()

            self.assertEqual(
                "DELETE FROM \"abc\" FOR PORTION OF \"valid_period\" FROM '2020-01-01' TO '2020-02-01'",
                str(q),
            )


class PostgresDeleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.table_abc = Table("abc")

    def test_delete_returning(self):
        q1 = (
            PostgreSQLQuery.from_(self.table_abc)
            .where(self.table_abc.foo == self.table_abc.bar)
            .delete()
            .returning(self.table_abc.id)
        )

        self.assertEqual('DELETE FROM "abc" WHERE "foo"="bar" RETURNING "id"', str(q1))

    def test_delete_returning_str(self):
        q1 = (
            PostgreSQLQuery.from_(self.table_abc)
            .where(self.table_abc.foo == self.table_abc.bar)
            .delete()
            .returning("id")
        )

        self.assertEqual('DELETE FROM "abc" WHERE "foo"="bar" RETURNING "id"', str(q1))

    def test_delete_returning_star(self):
        q1 = (
            PostgreSQLQuery.from_(self.table_abc)
            .where(self.table_abc.foo == self.table_abc.bar)
            .delete()
            .returning(Star())
        )

        self.assertEqual('DELETE FROM "abc" WHERE "foo"="bar" RETURNING *', str(q1))


class MySQLTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_delete_with_orderby_limit(self):
        q = MySQLQuery.from_(self.table_abc).orderby(self.table_abc.id).limit(1).delete()
        self.assertEqual("DELETE FROM `abc` ORDER BY `id` LIMIT 1", str(q))


class SQLiteTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_delete_with_orderby_limit(self):
        q = SQLLiteQuery.from_(self.table_abc).orderby(self.table_abc.id).limit(1).delete()
        self.assertEqual('DELETE FROM "abc" ORDER BY "id" LIMIT 1', str(q))
