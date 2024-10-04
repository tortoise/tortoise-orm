import unittest
from datetime import date

from pypika import (
    FormatParameter,
    NamedParameter,
    NumericParameter,
    Parameter,
    PyformatParameter,
    QmarkParameter,
    Query,
    Tables, DatePart,
)
from pypika.functions import Upper, Extract
from pypika.terms import ListParameter, ParameterValueWrapper, ValueWrapper


class ParametrizedTests(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_param_insert(self):
        q = (
            Query.into(self.table_abc)
            .columns("a", "b", "c")
            .insert(Parameter("?"), Parameter("?"), Parameter("?"))
        )

        self.assertEqual('INSERT INTO "abc" ("a","b","c") VALUES (?,?,?)', q.get_sql())

    def test_param_select_join(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.category == Parameter("%s"))
            .join(self.table_efg)
            .on(self.table_abc.id == self.table_efg.abc_id)
            .where(self.table_efg.date >= Parameter("%s"))
            .limit(10)
        )

        self.assertEqual(
            'SELECT * FROM "abc" JOIN "efg" ON "abc"."id"="efg"."abc_id" '
            'WHERE "abc"."category"=%s AND "efg"."date">=%s LIMIT 10',
            q.get_sql(),
        )

    def test_param_select_subquery(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.category == Parameter("&1"))
            .where(
                self.table_abc.id.isin(
                    Query.from_(self.table_efg)
                    .select(self.table_efg.abc_id)
                    .where(self.table_efg.date >= Parameter("&2"))
                )
            )
            .limit(10)
        )

        self.assertEqual(
            'SELECT * FROM "abc" WHERE "category"=&1 AND "id" IN '
            '(SELECT "abc_id" FROM "efg" WHERE "date">=&2) LIMIT 10',
            q.get_sql(),
        )

    def test_join(self):
        subquery = (
            Query.from_(self.table_efg)
            .select(self.table_efg.fiz, self.table_efg.buz)
            .where(self.table_efg.buz == Parameter(":buz"))
        )

        q = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(self.table_abc.bar == subquery.buz)
            .select(self.table_abc.foo, subquery.fiz)
            .where(self.table_abc.bar == Parameter(":bar"))
        )

        self.assertEqual(
            'SELECT "abc"."foo","sq0"."fiz" FROM "abc" JOIN (SELECT "fiz","buz" FROM "efg" WHERE "buz"=:buz)'
            ' "sq0" ON "abc"."bar"="sq0"."buz" WHERE "abc"."bar"=:bar',
            q.get_sql(),
        )

    def test_qmark_parameter(self):
        self.assertEqual("?", QmarkParameter().get_sql())

    def test_numeric_parameter(self):
        self.assertEqual(":14", NumericParameter("14").get_sql())
        self.assertEqual(":15", NumericParameter(15).get_sql())

    def test_named_parameter(self):
        self.assertEqual(":buz", NamedParameter("buz").get_sql())

    def test_format_parameter(self):
        self.assertEqual("%s", FormatParameter().get_sql())

    def test_pyformat_parameter(self):
        self.assertEqual("%(buz)s", PyformatParameter("buz").get_sql())


class ParametrizedTestsWithValues(unittest.TestCase):
    table_abc, table_efg = Tables("abc", "efg")

    def test_param_insert(self):
        q = Query.into(self.table_abc).columns("a", "b", "c").insert(1, 2.2, "foo")

        parameter = QmarkParameter()
        sql = q.get_sql(parameter=parameter)
        self.assertEqual('INSERT INTO "abc" ("a","b","c") VALUES (?,?,?)', sql)
        self.assertEqual([1, 2.2, "foo"], parameter.get_parameters())

    def test_param_select_join(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.category == "foobar")
            .join(self.table_efg)
            .on(self.table_abc.id == self.table_efg.abc_id)
            .where(self.table_efg.date >= date(2024, 2, 22))
            .limit(10)
        )

        parameter = FormatParameter()
        sql = q.get_sql(parameter=parameter)
        self.assertEqual(
            'SELECT * FROM "abc" JOIN "efg" ON "abc"."id"="efg"."abc_id" WHERE "abc"."category"=%s AND "efg"."date">=%s LIMIT 10',
            sql,
        )
        self.assertEqual(["foobar", date(2024, 2, 22)], parameter.get_parameters())

    def test_param_select_subquery(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.category == "foobar")
            .where(
                self.table_abc.id.isin(
                    Query.from_(self.table_efg)
                    .select(self.table_efg.abc_id)
                    .where(self.table_efg.date >= date(2024, 2, 22))
                )
            )
            .limit(10)
        )

        parameter = ListParameter(placeholder=lambda idx: f"&{idx+1}")
        sql = q.get_sql(parameter=parameter)
        self.assertEqual(
            'SELECT * FROM "abc" WHERE "category"=&1 AND "id" IN (SELECT "abc_id" FROM "efg" WHERE "date">=&2) LIMIT 10',
            sql,
        )
        self.assertEqual(["foobar", date(2024, 2, 22)], parameter.get_parameters())

    def test_join(self):
        subquery = (
            Query.from_(self.table_efg)
            .select(self.table_efg.fiz, self.table_efg.buz)
            .where(self.table_efg.buz == "buz")
        )

        q = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(self.table_abc.bar == subquery.buz)
            .select(self.table_abc.foo, subquery.fiz)
            .where(self.table_abc.bar == "bar")
        )

        parameter = NamedParameter()
        sql = q.get_sql(parameter=parameter)
        self.assertEqual(
            'SELECT "abc"."foo","sq0"."fiz" FROM "abc" JOIN (SELECT "fiz","buz" FROM "efg" WHERE "buz"=:param1)'
            ' "sq0" ON "abc"."bar"="sq0"."buz" WHERE "abc"."bar"=:param2',
            sql,
        )
        self.assertEqual({"param1": "buz", "param2": "bar"}, parameter.get_parameters())

    def test_join_with_parameter_value_wrapper(self):
        subquery = (
            Query.from_(self.table_efg)
            .select(self.table_efg.fiz, self.table_efg.buz)
            .where(self.table_efg.buz == ParameterValueWrapper(Parameter(":buz"), "buz"))
        )

        q = (
            Query.from_(self.table_abc)
            .join(subquery)
            .on(self.table_abc.bar == subquery.buz)
            .select(self.table_abc.foo, subquery.fiz)
            .where(self.table_abc.bar == ParameterValueWrapper(NamedParameter("bar"), "bar"))
        )

        parameter = NamedParameter()
        sql = q.get_sql(parameter=parameter)
        self.assertEqual(
            'SELECT "abc"."foo","sq0"."fiz" FROM "abc" JOIN (SELECT "fiz","buz" FROM "efg" WHERE "buz"=:buz)'
            ' "sq0" ON "abc"."bar"="sq0"."buz" WHERE "abc"."bar"=:bar',
            sql,
        )
        self.assertEqual({":buz": "buz", "bar": "bar"}, parameter.get_parameters())

    def test_pyformat_parameter(self):
        q = Query.into(self.table_abc).columns("a", "b", "c").insert(1, 2.2, "foo")

        parameter = PyformatParameter()
        sql = q.get_sql(parameter=parameter)
        self.assertEqual(
            'INSERT INTO "abc" ("a","b","c") VALUES (%(param1)s,%(param2)s,%(param3)s)', sql
        )
        self.assertEqual({"param1": 1, "param2": 2.2, "param3": "foo"}, parameter.get_parameters())

    def test_function_parameter_upper(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(self.table_abc.category == Upper(ValueWrapper("foobar")))
        )
        p = ListParameter("%s")
        sql = q.get_sql(parameter=p)
        self.assertEqual('SELECT * FROM "abc" WHERE "category"=UPPER(%s)', sql)

        self.assertEqual(["foobar"], p.get_parameters())

    def test_function_parameter_extract(self):
        q = (
            Query.from_(self.table_abc)
            .select("*")
            .where(Extract(DatePart.year, self.table_abc.date).eq(2024))
        )
        p = ListParameter("%s")
        sql = q.get_sql(parameter=p)
        self.assertEqual('SELECT * FROM "abc" WHERE EXTRACT(YEAR FROM "date")=%s', sql)
        self.assertEqual([2024], p.get_parameters())
