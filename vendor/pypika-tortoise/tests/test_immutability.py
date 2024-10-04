import unittest

from pypika import Query, Tables


class ImmutabilityTests(unittest.TestCase):
    table_a, table_b = Tables("a", "b")

    def test_select_returns_new_query_instance(self):
        query_a = Query.from_(self.table_a).select(self.table_a.foo)
        query_b = query_a.select(self.table_a.bar)

        self.assertIsNot(query_a, query_b)
        self.assertNotEqual(str(query_a), str(query_b))

    def test_queries_after_join(self):
        query1 = Query.from_(self.table_a).select(self.table_a.foo)
        query2 = (
            query1.join(self.table_b)
            .on(self.table_a.foo == self.table_b.bar)
            .select(self.table_b.buz)
        )

        self.assertEqual('SELECT "foo" FROM "a"', str(query1))
        self.assertEqual(
            'SELECT "a"."foo","b"."buz" FROM "a" JOIN "b" ON "a"."foo"="b"."bar"',
            str(query2),
        )

    def test_immutable_kwarg_on_query_builder_disables_immutability(self):
        query0 = Query.from_(self.table_a, immutable=False)
        query1 = query0.select(self.table_a.foo)
        self.assertIs(query0, query1)
