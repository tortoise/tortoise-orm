import unittest
from collections import OrderedDict

from pypika import JSON, Array, Field, QueryException, Table
from pypika.dialects import PostgreSQLQuery


class InsertTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_array_keyword(self):
        q = PostgreSQLQuery.into(self.table_abc).insert(1, [1, "a", True])

        self.assertEqual("INSERT INTO \"abc\" VALUES (1,ARRAY[1,'a',true])", str(q))

    def test_insert_ignore(self):
        q = PostgreSQLQuery.into("abc").insert((1, "a", True)).on_conflict().do_nothing()
        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true) ON CONFLICT DO NOTHING", str(q))

    def test_upsert(self):
        q = (
            PostgreSQLQuery.into("abc")
            .insert(1, "b", False)
            .as_("aaa")
            .on_conflict(self.table_abc.id)
            .do_update("abc")
        )
        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'b\',false) ON CONFLICT ("id") DO UPDATE SET "abc"=EXCLUDED."abc"',
            str(q),
        )


class JSONObjectTests(unittest.TestCase):
    def test_alias_set_correctly(self):
        table = Table("jsonb_table")
        q = PostgreSQLQuery.from_("abc").select(table.value.get_text_value("a").as_("name"))

        self.assertEqual('''SELECT "value"->>'a' "name" FROM "abc"''', str(q))

    def test_json_value_from_dict(self):
        q = PostgreSQLQuery.select(JSON({"a": "foo"}))

        self.assertEqual('SELECT \'{"a":"foo"}\'', str(q))

    def test_json_value_from_array_num(self):
        q = PostgreSQLQuery.select(JSON([1, 2, 3]))

        self.assertEqual("SELECT '[1,2,3]'", str(q))

    def test_json_value_from_array_str(self):
        q = PostgreSQLQuery.select(JSON(["a", "b", "c"]))

        self.assertEqual('SELECT \'["a","b","c"]\'', str(q))

    def test_json_value_from_dict_recursive(self):
        q = PostgreSQLQuery.select(JSON({"a": "z", "b": {"c": "foo"}, "d": 1}))

        # gotta split this one up to avoid the indeterminate order
        sql = str(q)
        start, end = 9, -2
        self.assertEqual("SELECT '{}'", sql[:start] + sql[end:])

        members_set = set(sql[start:end].split(","))
        self.assertSetEqual({'"a":"z"', '"b":{"c":"foo"}', '"d":1'}, members_set)


class JSONOperatorsTests(unittest.TestCase):
    # reference https://www.postgresql.org/docs/9.5/functions-json.html
    table_abc = Table("abc")

    def test_get_json_value_by_key(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.get_json_value("dates"))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"->\'dates\'', str(q))

    def test_get_json_value_by_index(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.get_json_value(1))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"->1', str(q))

    def test_get_text_value_by_key(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.get_text_value("dates"))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"->>\'dates\'', str(q))

    def test_get_text_value_by_index(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.get_text_value(1))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"->>1', str(q))

    def test_get_path_json_value(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.get_path_json_value("{a,b}"))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"#>\'{a,b}\'', str(q))

    def test_get_path_text_value(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.get_path_text_value("{a,b}"))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"#>>\'{a,b}\'', str(q))


class JSONBOperatorsTests(unittest.TestCase):
    # reference https://www.postgresql.org/docs/9.5/functions-json.html
    table_abc = Table("abc")

    def test_json_contains_for_json(self):
        q = PostgreSQLQuery.select(JSON({"a": 1, "b": 2}).contains({"a": 1}))

        # gotta split this one up to avoid the indeterminate order
        sql = str(q)
        start, end = 9, -13
        self.assertEqual("SELECT '{}'@>'{\"a\":1}'", sql[:start] + sql[end:])

        members_set = set(sql[start:end].split(","))
        self.assertSetEqual({'"a":1', '"b":2'}, members_set)

    def test_json_contains_for_field(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.contains({"dates": "2018-07-10 - 2018-07-17"}))
        )

        self.assertEqual(
            "SELECT * " 'FROM "abc" ' 'WHERE "json"@>\'{"dates":"2018-07-10 - 2018-07-17"}\'',
            str(q),
        )

    def test_json_contained_by_using_str_arg(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(
                self.table_abc.json.contained_by(
                    OrderedDict(
                        [
                            ("dates", "2018-07-10 - 2018-07-17"),
                            ("imported", "8"),
                        ]
                    )
                )
            )
        )
        self.assertEqual(
            'SELECT * FROM "abc" '
            'WHERE "json"<@\'{"dates":"2018-07-10 - 2018-07-17","imported":"8"}\'',
            str(q),
        )

    def test_json_contained_by_using_list_arg(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.contained_by(["One", "Two", "Three"]))
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"<@\'["One","Two","Three"]\'', str(q))

    def test_json_contained_by_with_complex_criterion(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(
                self.table_abc.json.contained_by(["One", "Two", "Three"])
                & (self.table_abc.id == 26)
            )
        )

        self.assertEqual(
            'SELECT * FROM "abc" WHERE "json"<@\'["One","Two","Three"]\' AND "id"=26',
            str(q),
        )

    def test_json_has_key(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.has_key("dates"))  # noqa: W601
        )

        self.assertEqual('SELECT * FROM "abc" WHERE "json"?\'dates\'', str(q))

    def test_json_has_keys(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.has_keys(["dates", "imported"]))
        )

        self.assertEqual("SELECT * FROM \"abc\" WHERE \"json\"?&ARRAY['dates','imported']", str(q))

    def test_json_has_any_keys(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.json.has_any_keys(["dates", "imported"]))
        )

        self.assertEqual("SELECT * FROM \"abc\" WHERE \"json\"?|ARRAY['dates','imported']", str(q))


class DistinctOnTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_distinct_on(self):
        q = (
            PostgreSQLQuery.from_(self.table_abc)
            .distinct_on("lname", self.table_abc.fname)
            .select("lname", "id")
        )

        self.assertEqual('''SELECT DISTINCT ON("lname","fname") "lname","id" FROM "abc"''', str(q))


class ArrayTests(unittest.TestCase):
    def test_array_syntax(self):
        tb = Table("tb")
        q = PostgreSQLQuery.from_(tb).select(Array(1, "a", ["b", 2, 3]))

        self.assertEqual(str(q), "SELECT ARRAY[1,'a',ARRAY['b',2,3]] FROM \"tb\"")

    def test_render_alias_in_array_sql(self):
        tb = Table("tb")

        q = PostgreSQLQuery.from_(tb).select(Array(tb.col).as_("different_name"))
        self.assertEqual(str(q), 'SELECT ARRAY["col"] "different_name" FROM "tb"')


class ReturningClauseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.table_abc = Table("abc")

    def test_returning_from_missing_table_raises_queryexception(self):
        field_from_diff_table = Field("xyz", table=Table("other"))

        with self.assertRaisesRegex(QueryException, "You can't return from other tables"):
            (
                PostgreSQLQuery.from_(self.table_abc)
                .where(self.table_abc.foo == self.table_abc.bar)
                .delete()
                .returning(field_from_diff_table)
            )

    def test_queryexception_if_returning_used_on_invalid_query(self):
        with self.assertRaisesRegex(QueryException, "Returning can't be used in this query"):
            PostgreSQLQuery.from_(self.table_abc).select("abc").returning("abc")

    def test_no_queryexception_if_returning_used_on_valid_query_type(self):
        # No exceptions for insert, update and delete queries
        with self.subTest("DELETE"):
            PostgreSQLQuery.from_(self.table_abc).where(
                self.table_abc.foo == self.table_abc.bar
            ).delete().returning("id")
        with self.subTest("UPDATE"):
            PostgreSQLQuery.update(self.table_abc).where(self.table_abc.foo == 0).set(
                "foo", "bar"
            ).returning("id")
        with self.subTest("INSERT"):
            PostgreSQLQuery.into(self.table_abc).insert("abc").returning("abc")

    def test_return_field_from_join_table(self):
        new_table = Table("xyz")
        q = (
            PostgreSQLQuery.update(self.table_abc)
            .join(new_table)
            .on(new_table.id == self.table_abc.xyz)
            .where(self.table_abc.foo == 0)
            .set("foo", "bar")
            .returning(new_table.a)
        )

        self.assertEqual(
            'UPDATE "abc" SET "foo"=\'bar\' FROM "abc" "abc_" JOIN "xyz" '
            'ON "xyz"."id"="abc"."xyz" WHERE "abc"."foo"=0 RETURNING "xyz"."a"',
            str(q),
        )
