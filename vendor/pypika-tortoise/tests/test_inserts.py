import unittest

from pypika import AliasedQuery, Case
from pypika import Field as F
from pypika import MySQLQuery, PostgreSQLQuery, Query, Table, Tables
from pypika import functions as fn
from pypika.functions import Avg
from pypika.terms import Values
from pypika.utils import QueryException

__author__ = "Timothy Heys"
__email__ = "theys@kayak.com"


class InsertIntoTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_insert_one_column(self):
        query = Query.into(self.table_abc).insert(1)

        self.assertEqual('INSERT INTO "abc" VALUES (1)', str(query))

    def test_insert_one_column_single_element_array(self):
        query = Query.into(self.table_abc).insert((1,))

        self.assertEqual('INSERT INTO "abc" VALUES (1)', str(query))

    def test_insert_one_column_multi_element_array(self):
        query = Query.into(self.table_abc).insert((1,), (2,))

        self.assertEqual('INSERT INTO "abc" VALUES (1),(2)', str(query))

    def test_insert_single_row_with_array_value(self):
        query = Query.into(self.table_abc).insert(1, ["a", "b", "c"])

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,['a','b','c'])", str(query))

    def test_insert_multiple_rows_with_array_value(self):
        query = Query.into(self.table_abc).insert(
            (1, ["a", "b", "c"]),
            (2, ["c", "d", "e"]),
        )

        self.assertEqual(
            'INSERT INTO "abc" ' "VALUES (1,['a','b','c']),(2,['c','d','e'])",
            str(query),
        )

    def test_insert_all_columns(self):
        query = Query.into(self.table_abc).insert(1, "a", True)

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true)", str(query))

    def test_insert_all_columns_single_element(self):
        query = Query.into(self.table_abc).insert((1, "a", True))

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true)", str(query))

    def test_insert_all_columns_multi_rows(self):
        query = Query.into(self.table_abc).insert((1, "a", True), (2, "b", False))

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true),(2,'b',false)", str(query))

    def test_insert_all_columns_multi_rows_chained(self):
        query = Query.into(self.table_abc).insert(1, "a", True).insert(2, "b", False)

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true),(2,'b',false)", str(query))

    def test_insert_all_columns_multi_rows_chained_mixed(self):
        query = (
            Query.into(self.table_abc).insert((1, "a", True), (2, "b", False)).insert(3, "c", True)
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES ' "(1,'a',true),(2,'b',false)," "(3,'c',true)",
            str(query),
        )

    def test_insert_all_columns_multi_rows_chained_multiple_rows(self):
        query = (
            Query.into(self.table_abc)
            .insert((1, "a", True), (2, "b", False))
            .insert((3, "c", True), (4, "d", False))
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES ' "(1,'a',true),(2,'b',false)," "(3,'c',true),(4,'d',false)",
            str(query),
        )

    def test_insert_selected_columns(self):
        query = (
            Query.into(self.table_abc)
            .columns(self.table_abc.foo, self.table_abc.bar, self.table_abc.buz)
            .insert(1, "a", True)
        )

        self.assertEqual('INSERT INTO "abc" ("foo","bar","buz") VALUES (1,\'a\',true)', str(query))

    def test_insert_empty_columns(self):
        query = Query.into(self.table_abc).columns().insert(1, "a", True)

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true)", str(query))

    def test_insert_selected_columns_type_list(self):
        query = (
            Query.into(self.table_abc)
            .columns([self.table_abc.foo, self.table_abc.bar, self.table_abc.buz])
            .insert(1, "a", True)
        )

        self.assertEqual('INSERT INTO "abc" ("foo","bar","buz") VALUES (1,\'a\',true)', str(query))

    def test_insert_empty_columns_type_list(self):
        query = Query.into(self.table_abc).columns([]).insert(1, "a", True)

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true)", str(query))

    def test_insert_selected_columns_type_tuple(self):
        query = (
            Query.into(self.table_abc)
            .columns((self.table_abc.foo, self.table_abc.bar, self.table_abc.buz))
            .insert(1, "a", True)
        )

        self.assertEqual('INSERT INTO "abc" ("foo","bar","buz") VALUES (1,\'a\',true)', str(query))

    def test_insert_empty_columns_type_tuple(self):
        query = Query.into(self.table_abc).columns(()).insert(1, "a", True)

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true)", str(query))

    def test_insert_none_skipped(self):
        query = Query.into(self.table_abc).insert()

        self.assertEqual("", str(query))

    def test_insert_null(self):
        query = Query.into(self.table_abc).insert(None)

        self.assertEqual('INSERT INTO "abc" VALUES (NULL)', str(query))

    def test_insert_column_using_table_alias(self):
        q = self.table_abc.insert(1)
        self.assertEqual('INSERT INTO "abc" VALUES (1)', str(q))

    def test_insert_column_using_alias_with_chain(self):
        q = self.table_abc.insert(1, "a", True).insert(2, "b", False)
        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true),(2,'b',false)", str(q))

    def test_insert_with_statement(self):
        sub_query = Query().select(self.table_abc.id).from_(self.table_abc)
        aliased = AliasedQuery("sub_qs")

        q = (
            Query()
            .with_(sub_query, "sub_qs")
            .into(self.table_abc)
            .select(aliased.id)
            .from_(aliased)
        )
        self.assertEqual(
            'WITH sub_qs AS (SELECT "id" FROM "abc") INSERT INTO "abc" SELECT "sub_qs"."id" FROM sub_qs',
            str(q),
        )


class PostgresInsertIntoOnConflictTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_insert_on_conflict_do_nothing_field(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1)
            .on_conflict(self.table_abc.id)
            .do_nothing()
        )

        self.assertEqual('INSERT INTO "abc" VALUES (1) ON CONFLICT ("id") DO NOTHING', str(query))

    def test_insert_on_conflict_do_nothing_multiple_fields(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1)
            .on_conflict(self.table_abc.id, self.table_abc.sub_id)
            .do_nothing()
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1) ON CONFLICT ("id", "sub_id") DO NOTHING', str(query)
        )

    def test_insert_on_conflict_do_nothing_field_str(self):
        query = PostgreSQLQuery.into(self.table_abc).insert(1).on_conflict("id").do_nothing()

        self.assertEqual('INSERT INTO "abc" VALUES (1) ON CONFLICT ("id") DO NOTHING', str(query))

    def test_insert_on_conflict_do_nothing_multiple_fields_str(self):
        query = (
            PostgreSQLQuery.into(self.table_abc).insert(1).on_conflict("id", "sub_id").do_nothing()
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1) ON CONFLICT ("id", "sub_id") DO NOTHING', str(query)
        )

    def test_insert_on_conflict_do_nothing_mixed_fields(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1)
            .on_conflict("id", self.table_abc.sub_id)
            .do_nothing()
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1) ON CONFLICT ("id", "sub_id") DO NOTHING', str(query)
        )

    def test_insert_on_conflict_do_update_field(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict(self.table_abc.id)
            .do_update(self.table_abc.name, "m")
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'m\') ON CONFLICT ("id") DO UPDATE SET "name"=\'m\'',
            str(query),
        )

    def test_insert_on_conflict_do_update_multiple_fields(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict(self.table_abc.id, self.table_abc.sub_id)
            .do_update(self.table_abc.name, "m")
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'m\') ON CONFLICT ("id", "sub_id") DO UPDATE SET "name"=\'m\'',
            str(query),
        )

    def test_insert_on_conflict_do_update_field_str(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict("id")
            .do_update("name", "m")
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'m\') ON CONFLICT ("id") DO UPDATE SET "name"=\'m\'',
            str(query),
        )

    def test_insert_on_conflict_do_update_multiple_fields_str(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict("id", "sub_id")
            .do_update("name", "m")
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'m\') ON CONFLICT ("id", "sub_id") DO UPDATE SET "name"=\'m\'',
            str(query),
        )

    def test_insert_on_conflict_do_update_multiple_mixed_fields(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict("id", self.table_abc.sub_id)
            .do_update("name", "m")
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'m\') ON CONFLICT ("id", "sub_id") DO UPDATE SET "name"=\'m\'',
            str(query),
        )

    def test_insert_on_conflict_no_handler(self):
        with self.assertRaises(QueryException):
            str(PostgreSQLQuery.into(self.table_abc).insert(1).on_conflict(self.table_abc.id))

    def test_insert_on_conflict_two_handlers_do_nothing(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.into(self.table_abc)
                .insert(1)
                .on_conflict("id")
                .do_nothing()
                .do_update(self.table_abc.name, "m")
            )

    def test_insert_on_conflict_two_handlers_do_update(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.into(self.table_abc)
                .insert(1)
                .on_conflict(self.table_abc.id)
                .do_update(self.table_abc.name, "m")
                .do_nothing()
            )

    def test_non_insert_on_conflict_do_nothing(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.update(self.table_abc)
                .set("foo", "bar")
                .on_conflict("id")
                .do_nothing()
            )

    def test_non_insert_on_conflict_do_update(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.update(self.table_abc)
                .set("foo", "bar")
                .on_conflict("id")
                .do_update(["name"], ["m"])
            )

    def test_insert_on_fieldless_conflict_do_nothing(self):
        query = PostgreSQLQuery.into(self.table_abc).insert(1).on_conflict(None).do_nothing()

        self.assertEqual('INSERT INTO "abc" VALUES (1) ON CONFLICT DO NOTHING', str(query))

    def test_insert_on_fieldless_conflict_do_update_field(self):
        with self.assertRaises(QueryException):
            str(
                PostgreSQLQuery.into(self.table_abc)
                .insert(1, "m")
                .on_conflict(None)
                .do_update(self.table_abc.name, "m")
            )

    def test_on_conflict_from_subquery(self):
        table_bcd = Table("bcd")
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(self.table_abc.fname, self.table_abc.lname)
            .select(table_bcd.fname, table_bcd.lname)
            .from_(table_bcd)
            .on_conflict(self.table_abc.id, self.table_abc.sub_id)
            .do_update(self.table_abc.fname, 1)
            .do_update(self.table_abc.lname, table_bcd.lname)
            .do_update(
                self.table_abc.cname,
                Case()
                .when(self.table_abc.cname.eq("cname"), "new_name")
                .else_(self.table_abc.cname),
            )
        )

        self.assertEqual(
            'INSERT INTO "abc" VALUES ("fname","lname") '
            'ON CONFLICT ("id", "sub_id") '
            'DO UPDATE SET "fname"=1,"lname"="bcd"."lname",'
            '"cname"=CASE WHEN "abc"."cname"=\'cname\' THEN \'new_name\' ELSE "abc"."cname" END',
            str(query),
        )

    def test_on_conflict_where_empty_conflict_fields_do_nothing(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.into(self.table_abc)
                .insert(1, "m")
                .on_conflict()
                .where(self.table_abc.abc.eq(0))
                .where(self.table_abc.cde.eq(0))
                .do_nothing()
            )

    def test_on_conflict_where_conflict_fields_do_nothing(self):
        qs = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict("id")
            .where(self.table_abc.abc.eq(0))
            .where(self.table_abc.cde.eq(0))
            .do_nothing()
        )
        self.assertEqual(
            """INSERT INTO "abc" VALUES (1,'m') ON CONFLICT ("id") WHERE "abc"=0 AND "cde"=0 DO NOTHING""",
            str(qs),
        )

    def test_on_conflict_where_empty_conflict_fields_do_update(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.into(self.table_abc)
                .insert(1, "m")
                .on_conflict()
                .where(self.table_abc.abc.eq(0))
                .where(self.table_abc.cde.eq(0))
                .do_update("field", "val")
            )

    def test_on_conflict_where_conflict_fields_do_update(self):
        qs = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict("id")
            .where(self.table_abc.abc.eq(0))
            .where(self.table_abc.cde.eq(0))
            .do_update("field", "val")
        )
        self.assertEqual(
            """INSERT INTO "abc" VALUES (1,'m') ON CONFLICT ("id") WHERE "abc"=0 AND "cde"=0 """
            """DO UPDATE SET "field"='val\'""",
            str(qs),
        )

    def test_where_and_on_conflict_where(self):
        table_bcd = Table("bcd")

        qs = (
            PostgreSQLQuery.into(self.table_abc)
            .select(table_bcd.abc)
            .from_(table_bcd)
            .where(table_bcd.abc.eq("1"))
            .on_conflict("id")
            .where(self.table_abc.abc.eq(0))
            .where(self.table_abc.cde.eq(0))
            .do_update("field", "val")
        )

        self.assertEqual(
            'INSERT INTO "abc" SELECT "abc" FROM "bcd" WHERE "abc"=\'1\' '
            'ON CONFLICT ("id") WHERE "abc"=0 AND "cde"=0 DO UPDATE SET "field"=\'val\'',
            str(qs),
        )

    def test_on_conflict_do_nothing_where(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.into(self.table_abc)
                .insert(1, "m")
                .on_conflict()
                .do_nothing()
                .where(self.table_abc.abc.eq(1))
            )

    def test_empty_on_conflict_do_update_where(self):
        with self.assertRaises(QueryException):
            (
                PostgreSQLQuery.into(self.table_abc)
                .insert(1, "m")
                .on_conflict()
                .do_update("abc", 1)
                .where(self.table_abc.abc.eq(1))
            )

    def test_on_conflict_do_update_where(self):
        qs = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict("id")
            .do_update("abc", 1)
            .where(self.table_abc.abc.eq(1))
        )
        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'m\') ON CONFLICT ("id") DO UPDATE SET "abc"=1 WHERE "abc"."abc"=1',
            str(qs),
        )

    def test_on_conflict_do_update_with_excluded_where(self):
        qs = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "m")
            .on_conflict("id")
            .do_update("abc")
            .where(self.table_abc.abc.eq(1))
        )
        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'m\') ON CONFLICT ("id") DO UPDATE SET "abc"=EXCLUDED."abc" WHERE '
            '"abc"."abc"=1',
            str(qs),
        )

    def test_on_conflict_where_complex(self):
        table_bcd = Table("bcd")

        qs = (
            PostgreSQLQuery.into(self.table_abc)
            .select(table_bcd.abc)
            .from_(table_bcd)
            .where(table_bcd.abc.eq("1"))
            .on_conflict("id")
            .where(self.table_abc.abc.eq(0))
            .where(self.table_abc.cde.eq(0))
            .do_update("field", "val")
            .where(self.table_abc.id.eq(2))
            .where(self.table_abc.sub_id.eq(3))
        )
        self.assertEqual(
            'INSERT INTO "abc" SELECT "abc" FROM "bcd" WHERE "abc"=\'1\' '
            'ON CONFLICT ("id") WHERE "abc"=0 AND "cde"=0 '
            'DO UPDATE SET "field"=\'val\' WHERE "abc"."id"=2 AND "abc"."sub_id"=3',
            str(qs),
        )


class PostgresInsertIntoReturningTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_insert_returning_one_field(self):
        query = PostgreSQLQuery.into(self.table_abc).insert(1).returning(self.table_abc.id)

        self.assertEqual('INSERT INTO "abc" VALUES (1) RETURNING "id"', str(query))

    def test_insert_returning_one_field_str(self):
        query = PostgreSQLQuery.into(self.table_abc).insert(1).returning("id")

        self.assertEqual('INSERT INTO "abc" VALUES (1) RETURNING "id"', str(query))

    def test_insert_returning_all_fields(self):
        query = PostgreSQLQuery.into(self.table_abc).insert(1).returning(self.table_abc.star)

        self.assertEqual('INSERT INTO "abc" VALUES (1) RETURNING *', str(query))

    def test_insert_returning_all_fields_and_arithmetics(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1)
            .returning(self.table_abc.star, self.table_abc.f1 + self.table_abc.f2)
        )

        self.assertEqual('INSERT INTO "abc" VALUES (1) RETURNING *,"f1"+"f2"', str(query))

    def test_insert_all_columns_multi_rows_chained_returning_star(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "a", True)
            .insert(2, "b", False)
            .returning(self.table_abc.star)
        )

        self.assertEqual(
            "INSERT INTO \"abc\" VALUES (1,'a',true),(2,'b',false) RETURNING *",
            str(query),
        )

    def test_insert_all_columns_multi_rows_chained_returning_star_and_id(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "a", True)
            .insert(2, "b", False)
            .returning(
                self.table_abc.name,
                self.table_abc.star,
                self.table_abc.id,
            )
        )

        self.assertEqual(
            "INSERT INTO \"abc\" VALUES (1,'a',true),(2,'b',false) RETURNING *",
            str(query),
        )

    def test_insert_all_columns_multi_rows_chained_returning_star_str(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1, "a", True)
            .insert(2, "b", False)
            .returning("*")
        )

        self.assertEqual(
            "INSERT INTO \"abc\" VALUES (1,'a',true),(2,'b',false) RETURNING *",
            str(query),
        )

    def test_insert_all_columns_single_element_arrays(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert((1, "a", True))
            .returning(self.table_abc.star)
        )

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true) RETURNING *", str(query))

    def test_insert_returning_null(self):
        query = PostgreSQLQuery.into(self.table_abc).insert(1).returning(None)

        self.assertEqual('INSERT INTO "abc" VALUES (1) RETURNING NULL', str(query))

    def test_insert_returning_tuple(self):
        query = PostgreSQLQuery.into(self.table_abc).insert(1).returning((1, 2, 3))

        self.assertEqual('INSERT INTO "abc" VALUES (1) RETURNING (1,2,3)', str(query))

    def test_insert_returning_arithmetics(self):
        query = (
            PostgreSQLQuery.into(self.table_abc)
            .insert(1)
            .returning(self.table_abc.f1 + self.table_abc.f2)
        )

        self.assertEqual('INSERT INTO "abc" VALUES (1) RETURNING "f1"+"f2"', str(query))

    def test_insert_returning_aggregate(self):
        with self.assertRaises(QueryException):
            PostgreSQLQuery.into(self.table_abc).insert(1).returning(Avg(self.table_abc.views))

    def test_insert_returning_from_other_table(self):
        table_cba = Table("cba")
        with self.assertRaises(QueryException):
            PostgreSQLQuery.into(self.table_abc).insert(1).returning(table_cba.id)


class InsertIntoOnDuplicateTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_insert_one_column(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1)
            .on_conflict()
            .do_update(self.table_abc.foo, self.table_abc.foo)
        )
        self.assertEqual(
            "INSERT INTO `abc` VALUES (1) ON DUPLICATE KEY UPDATE `foo`=`foo`",
            str(query),
        )

    def test_insert_one_column_using_values(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1)
            .on_conflict()
            .do_update(self.table_abc.foo, Values(self.table_abc.foo))
        )
        self.assertEqual(
            "INSERT INTO `abc` VALUES (1) ON DUPLICATE KEY UPDATE `foo`=VALUES(`foo`)",
            str(query),
        )

    def test_insert_one_column_single_element_array(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert((1,))
            .on_conflict()
            .do_update(self.table_abc.foo, self.table_abc.foo)
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1) ON DUPLICATE KEY UPDATE `foo`=`foo`",
            str(query),
        )

    def test_insert_one_column_multi_element_array(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert((1,), (2,))
            .on_conflict()
            .do_update(self.table_abc.foo, self.table_abc.foo)
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1),(2) ON DUPLICATE KEY UPDATE `foo`=`foo`",
            str(query),
        )

    def test_insert_multiple_columns_on_duplicate_update_one_with_same_value(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1, "a")
            .on_conflict()
            .do_update(self.table_abc.bar, Values(self.table_abc.bar))
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,'a') ON DUPLICATE KEY UPDATE `bar`=VALUES(`bar`)",
            str(query),
        )

    def test_insert_multiple_columns_on_duplicate_update_one_with_different_value(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1, "a")
            .on_conflict()
            .do_update(self.table_abc.bar, "b")
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,'a') ON DUPLICATE KEY UPDATE `bar`='b'",
            str(query),
        )

    def test_insert_multiple_columns_on_duplicate_update_one_with_expression(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1, 2)
            .on_conflict()
            .do_update(self.table_abc.bar, 4 + F("bar"))
        )  # todo sql expression? not python

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,2) ON DUPLICATE KEY UPDATE `bar`=4+`bar`",
            str(query),
        )

    def test_insert_multiple_columns_on_duplicate_update_one_with_expression_using_original_field_value(
        self,
    ):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1, "a")
            .on_conflict()
            .do_update(self.table_abc.bar, fn.Concat(self.table_abc.bar, "update"))
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,'a') ON DUPLICATE KEY UPDATE `bar`=CONCAT(`bar`,'update')",
            str(query),
        )

    def test_insert_multiple_columns_on_duplicate_update_one_with_expression_using_values(
        self,
    ):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1, "a")
            .on_conflict()
            .do_update(self.table_abc.bar, fn.Concat(Values(self.table_abc.bar), "update"))
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,'a') ON DUPLICATE KEY UPDATE `bar`=CONCAT(VALUES(`bar`),'update')",
            str(query),
        )

    def test_insert_multiple_columns_on_duplicate_update_multiple(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1, "a", "b")
            .on_conflict()
            .do_update(self.table_abc.bar, "b")
            .do_update(self.table_abc.baz, "c")
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,'a','b') ON DUPLICATE KEY UPDATE `bar`='b',`baz`='c'",
            str(query),
        )

    def test_insert_multi_rows_chained_mixed_on_duplicate_update_multiple(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert((1, "a", True), (2, "b", False))
            .insert(3, "c", True)
            .on_conflict()
            .do_update(self.table_abc.foo, self.table_abc.foo)
            .do_update(self.table_abc.bar, Values(self.table_abc.bar))
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1,'a',true),(2,'b',false),(3,'c',true) "
            "ON DUPLICATE KEY UPDATE `foo`=`foo`,`bar`=VALUES(`bar`)",
            str(query),
        )

    def test_insert_selected_columns_on_duplicate_update_one(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .columns(self.table_abc.foo, self.table_abc.bar, self.table_abc.baz)
            .insert(1, "a", True)
            .on_conflict()
            .do_update(self.table_abc.baz, False)
        )

        self.assertEqual(
            "INSERT INTO `abc` (`foo`,`bar`,`baz`) VALUES (1,'a',true) ON DUPLICATE KEY UPDATE `baz`=false",
            str(query),
        )

    def test_insert_selected_columns_on_duplicate_update_multiple(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .columns(self.table_abc.foo, self.table_abc.bar, self.table_abc.baz)
            .insert(1, "a", True)
            .on_conflict()
            .do_update(self.table_abc.baz, False)
            .do_update(self.table_abc.bar, Values(self.table_abc.bar))
        )

        self.assertEqual(
            "INSERT INTO `abc` (`foo`,`bar`,`baz`) VALUES (1,'a',true) "
            "ON DUPLICATE KEY UPDATE `baz`=false,`bar`=VALUES(`bar`)",
            str(query),
        )

    def test_insert_none_skipped(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert()
            .on_conflict()
            .do_update(self.table_abc.baz, False)
        )

        self.assertEqual("", str(query))

    def test_insert_ignore(self):
        query = (
            MySQLQuery.into(self.table_abc)
            .insert(1)
            .on_conflict()
            .do_update(self.table_abc.baz, False)
        )

        self.assertEqual(
            "INSERT INTO `abc` VALUES (1) ON DUPLICATE KEY UPDATE `baz`=false",
            str(query),
        )


class InsertSelectFromTests(unittest.TestCase):
    table_abc, table_efg, table_hij = Tables("abc", "efg", "hij")

    def test_insert_star(self):
        query = Query.into(self.table_abc).from_(self.table_efg).select("*")

        self.assertEqual('INSERT INTO "abc" SELECT * FROM "efg"', str(query))

    def test_insert_ignore_star(self):
        query = (
            Query.into(self.table_abc).from_(self.table_efg).select("*").on_conflict().do_nothing()
        )

        self.assertEqual('INSERT INTO "abc" SELECT * FROM "efg" ON CONFLICT DO NOTHING', str(query))

    def test_insert_from_columns(self):
        query = (
            Query.into(self.table_abc)
            .from_(self.table_efg)
            .select(self.table_efg.fiz, self.table_efg.buz, self.table_efg.baz)
        )

        self.assertEqual('INSERT INTO "abc" ' 'SELECT "fiz","buz","baz" FROM "efg"', str(query))

    def test_insert_columns_from_star(self):
        query = (
            Query.into(self.table_abc)
            .columns(
                self.table_abc.foo,
                self.table_abc.bar,
                self.table_abc.buz,
            )
            .from_(self.table_efg)
            .select("*")
        )

        self.assertEqual('INSERT INTO "abc" ("foo","bar","buz") ' 'SELECT * FROM "efg"', str(query))

    def test_insert_columns_from_columns(self):
        query = (
            Query.into(self.table_abc)
            .columns(self.table_abc.foo, self.table_abc.bar, self.table_abc.buz)
            .from_(self.table_efg)
            .select(self.table_efg.fiz, self.table_efg.buz, self.table_efg.baz)
        )

        self.assertEqual(
            'INSERT INTO "abc" ("foo","bar","buz") ' 'SELECT "fiz","buz","baz" FROM "efg"',
            str(query),
        )

    def test_insert_columns_from_columns_with_join(self):
        query = (
            Query.into(self.table_abc)
            .columns(
                self.table_abc.c1,
                self.table_abc.c2,
                self.table_abc.c3,
                self.table_abc.c4,
            )
            .from_(self.table_efg)
            .select(self.table_efg.foo, self.table_efg.bar)
            .join(self.table_hij)
            .on(self.table_efg.id == self.table_hij.abc_id)
            .select(self.table_hij.fiz, self.table_hij.buz)
        )

        self.assertEqual(
            'INSERT INTO "abc" ("c1","c2","c3","c4") '
            'SELECT "efg"."foo","efg"."bar","hij"."fiz","hij"."buz" FROM "efg" '
            'JOIN "hij" ON "efg"."id"="hij"."abc_id"',
            str(query),
        )


class InsertSubqueryTests(unittest.TestCase):
    def test_insert_subquery_wrapped_in_brackets(self):
        purchase_order_item, part = Tables("purchase_order_item", "part")

        q = (
            Query.into(purchase_order_item)
            .columns(purchase_order_item.id_part, purchase_order_item.id_customer)
            .insert(
                Query.from_(part).select(part.part_id).where(part.part_number == "FOOBAR"),
                12345,
            )
        )

        self.assertEqual(
            'INSERT INTO "purchase_order_item" '
            '("id_part","id_customer") '
            "VALUES "
            '((SELECT "part_id" FROM "part" WHERE "part_number"=\'FOOBAR\'),12345)',
            str(q),
        )


class SelectIntoTests(unittest.TestCase):
    table_abc, table_efg, table_hij = Tables("abc", "efg", "hij")

    def test_select_star_into(self):
        query = Query.from_(self.table_abc).select("*").into(self.table_efg)

        self.assertEqual('SELECT * INTO "efg" FROM "abc"', str(query))

    def test_select_columns_into(self):
        query = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar, self.table_abc.buz)
            .into(self.table_efg)
        )

        self.assertEqual('SELECT "foo","bar","buz" INTO "efg" FROM "abc"', str(query))

    def test_select_columns_into_with_join(self):
        query = (
            Query.from_(self.table_abc)
            .select(self.table_abc.foo, self.table_abc.bar)
            .join(self.table_hij)
            .on(self.table_abc.id == self.table_hij.abc_id)
            .select(self.table_hij.fiz, self.table_hij.buz)
            .into(self.table_efg)
        )

        self.assertEqual(
            'SELECT "abc"."foo","abc"."bar","hij"."fiz","hij"."buz" '
            'INTO "efg" FROM "abc" '
            'JOIN "hij" ON "abc"."id"="hij"."abc_id"',
            str(query),
        )


class ReplaceTests(unittest.TestCase):
    table_abc, table_def = Tables("abc", "efg")

    def test_replace_simple(self):
        query = Query.into(self.table_abc).replace("v1", "v2", "v3")
        expected_output = "REPLACE INTO \"abc\" VALUES ('v1','v2','v3')"
        self.assertEqual(str(query), expected_output)

    def test_replace_subquery(self):
        query = Query.into(self.table_abc).replace(Query.from_(self.table_def).select("f1", "f2"))
        expected_output = 'REPLACE INTO "abc" VALUES ((SELECT "f1","f2" FROM "efg"))'
        self.assertEqual(str(query), expected_output)
