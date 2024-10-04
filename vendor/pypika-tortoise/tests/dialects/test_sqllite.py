import unittest

from pypika import Table
from pypika.dialects import SQLLiteQuery


class SelectTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_bool_true_as_one(self):
        q = SQLLiteQuery.from_("abc").select(True)

        self.assertEqual('SELECT 1 FROM "abc"', str(q))

    def test_bool_false_as_zero(self):
        q = SQLLiteQuery.from_("abc").select(False)

        self.assertEqual('SELECT 0 FROM "abc"', str(q))


class InsertTests(unittest.TestCase):
    table_abc = Table("abc")

    def test_insert_ignore(self):
        q = SQLLiteQuery.into("abc").insert((1, "a", True)).on_conflict().do_nothing()
        self.assertEqual("INSERT INTO \"abc\" VALUES (1,'a',true) ON CONFLICT DO NOTHING", str(q))

    def test_upsert(self):
        q = (
            SQLLiteQuery.into("abc")
            .insert(1, "b", False)
            .as_("aaa")
            .on_conflict(self.table_abc.id)
            .do_update("abc")
        )
        self.assertEqual(
            'INSERT INTO "abc" VALUES (1,\'b\',false) ON CONFLICT ("id") DO UPDATE SET "abc"=EXCLUDED."abc"',
            str(q),
        )
