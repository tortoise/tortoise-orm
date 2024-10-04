import unittest

from pypika import (
    SYSTEM_TIME,
    AliasedQuery,
    MySQLQuery,
    PostgreSQLQuery,
    Query,
    SQLLiteQuery,
    Table,
)

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"

from pypika.terms import Star


class UpdateTests(unittest.TestCase):
    table_abc = Table("abc")
    table_def = Table("def")

    def test_empty_query(self):
        q = Query.update("abc")

        self.assertEqual("", str(q))

    def test_omit_where(self):
        q = Query.update(self.table_abc).set("foo", "bar")

        self.assertEqual('UPDATE "abc" SET "foo"=\'bar\'', str(q))

    def test_single_quote_escape_in_set(self):
        q = Query.update(self.table_abc).set("foo", "bar'foo")

        self.assertEqual("UPDATE \"abc\" SET \"foo\"='bar''foo'", str(q))

    def test_update__table_schema(self):
        table = Table("abc", "schema1")
        q = Query.update(table).set(table.foo, 1).where(table.foo == 0)

        self.assertEqual('UPDATE "schema1"."abc" SET "foo"=1 WHERE "foo"=0', str(q))

    def test_update_with_none(self):
        q = Query.update("abc").set("foo", None)
        self.assertEqual('UPDATE "abc" SET "foo"=null', str(q))

    def test_update_from(self):
        from_table = Table("from_table")

        q = (
            Query.update(self.table_abc)
            .set(self.table_abc.lname, from_table.long_name)
            .from_(from_table)
        )
        self.assertEqual(
            'UPDATE "abc" SET "lname"="from_table"."long_name" FROM "from_table"', str(q)
        )

    def test_update_from_with_where(self):
        from_table = Table("from_table")

        q = (
            Query.update(self.table_abc)
            .set(self.table_abc.lname, from_table.long_name)
            .from_(from_table)
            .where(self.table_abc.fname.eq(from_table.full_name))
        )
        self.assertEqual(
            'UPDATE "abc" SET "lname"="from_table"."long_name" FROM "from_table" '
            'WHERE "abc"."fname"="from_table"."full_name"',
            str(q),
        )

    def test_update_with_statement(self):
        table_efg = Table("efg")

        sub_query = Query.from_(table_efg).select("fizz")
        an_alias = AliasedQuery("an_alias")

        q = (
            Query.with_(sub_query, "an_alias")
            .update(self.table_abc)
            .from_(an_alias)
            .set(self.table_abc.lname, an_alias.long_name)
            .where(self.table_abc.comp.eq(an_alias.alias_comp))
        )
        self.assertEqual(
            'WITH an_alias AS (SELECT "fizz" FROM "efg") '
            'UPDATE "abc" SET "lname"="an_alias"."long_name" FROM an_alias '
            'WHERE "abc"."comp"="an_alias"."alias_comp"',
            str(q),
        )

    def test_for_portion(self):
        with self.subTest("with system time"):
            q = Query.update(
                self.table_abc.for_portion(SYSTEM_TIME.from_to("2020-01-01", "2020-02-01"))
            ).set("foo", "bar")

            self.assertEqual(
                "UPDATE \"abc\" FOR PORTION OF SYSTEM_TIME FROM '2020-01-01' TO '2020-02-01' SET \"foo\"='bar'",
                str(q),
            )

        with self.subTest("with column"):
            q = Query.update(
                self.table_abc.for_portion(
                    self.table_abc.valid_period.from_to("2020-01-01", "2020-02-01")
                )
            ).set("foo", "bar")

            self.assertEqual(
                "UPDATE \"abc\" FOR PORTION OF \"valid_period\" FROM '2020-01-01' TO '2020-02-01' SET \"foo\"='bar'",
                str(q),
            )


class PostgresUpdateTests(unittest.TestCase):
    table_abc = Table("abc")
    table_def = Table("def")

    def test_update_returning_str(self):
        q = (
            PostgreSQLQuery.update(self.table_abc)
            .where(self.table_abc.foo == 0)
            .set("foo", "bar")
            .returning("id")
        )

        self.assertEqual(
            'UPDATE "abc" SET "foo"=\'bar\' WHERE "foo"=0 RETURNING "abc"."id"', str(q)
        )

    def test_update_returning(self):
        q = (
            PostgreSQLQuery.update(self.table_abc)
            .where(self.table_abc.foo == 0)
            .set("foo", "bar")
            .returning(self.table_abc.id)
        )

        self.assertEqual(
            'UPDATE "abc" SET "foo"=\'bar\' WHERE "foo"=0 RETURNING "abc"."id"', str(q)
        )

    def test_update_returning_from_different_tables(self):
        table_bcd = Table("bcd")

        q = (
            PostgreSQLQuery.update(self.table_abc)
            .from_(table_bcd)
            .set(self.table_abc.lname, table_bcd.long_name)
            .returning(self.table_abc.id, table_bcd.fname)
        )
        self.assertEqual(
            'UPDATE "abc" SET "lname"="bcd"."long_name" FROM "bcd" RETURNING "abc"."id","bcd"."fname"',
            str(q),
        )

    def test_update_returning_star(self):
        q = (
            PostgreSQLQuery.update(self.table_abc)
            .where(self.table_abc.foo == 0)
            .set("foo", "bar")
            .returning(Star())
        )

        self.assertEqual('UPDATE "abc" SET "foo"=\'bar\' WHERE "foo"=0 RETURNING *', str(q))

    def test_update_with_join(self):
        q = (
            PostgreSQLQuery.update(self.table_abc)
            .join(self.table_def)
            .on(self.table_def.abc_id == self.table_abc.id)
            .set(self.table_abc.lname, self.table_def.lname)
        )
        self.assertEqual(
            'UPDATE "abc" SET "lname"="def"."lname" FROM "abc" "abc_" JOIN "def" ON "def"."abc_id"="abc"."id"',
            str(q),
        )


class SQLLiteUpdateTests(unittest.TestCase):
    table_abc = Table("abc")
    table_def = Table("def")

    def test_update_with_bool(self):
        q = SQLLiteQuery.update(self.table_abc).set(self.table_abc.foo, True)

        self.assertEqual('UPDATE "abc" SET "foo"=1', str(q))

    def test_update_with_limit_order(self):
        q = (
            SQLLiteQuery.update(self.table_abc)
            .set(self.table_abc.lname, "test")
            .limit(1)
            .orderby(self.table_abc.id)
        )
        self.assertEqual('UPDATE "abc" SET "lname"=\'test\' ORDER BY "id" LIMIT 1', str(q))

    def test_update_with_join(self):
        q = (
            SQLLiteQuery.update(self.table_abc)
            .join(self.table_def)
            .on(self.table_def.abc_id == self.table_abc.id)
            .set(self.table_abc.lname, self.table_def.lname)
        )
        self.assertEqual(
            'UPDATE "abc" SET "lname"="def"."lname" FROM "abc" "abc_" JOIN "def" ON "def"."abc_id"="abc"."id"',
            str(q),
        )


class MySQLUpdateTests(unittest.TestCase):
    table_abc = Table("abc")
    table_def = Table("def")

    def test_update_with_limit_order(self):
        q = (
            MySQLQuery.update(self.table_abc)
            .set(self.table_abc.lname, "test")
            .limit(1)
            .orderby(self.table_abc.id)
        )
        self.assertEqual("UPDATE `abc` SET `lname`='test' ORDER BY `id` LIMIT 1", str(q))

    def test_update_with_join(self):
        q = (
            MySQLQuery.update(self.table_abc)
            .join(self.table_def)
            .on(self.table_def.abc_id == self.table_abc.id)
            .set(self.table_abc.lname, self.table_def.lname)
        )
        self.assertEqual(
            "UPDATE `abc` JOIN `def` ON `def`.`abc_id`=`abc`.`id` SET `lname`=`def`.`lname`",
            str(q),
        )
