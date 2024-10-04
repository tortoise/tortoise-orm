import unittest

from pypika import Query, Table
from pypika.pseudocolumns import ColumnValue, ObjectID, ObjectValue, RowID, RowNum, SysDate
from pypika.terms import PseudoColumn


class PseudoColumnsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(PseudoColumnsTest, cls).setUpClass()
        cls.table1 = Table("table1")

    def test_column_value(self):
        self.assertEqual("COLUMN_VALUE", ColumnValue)

    def test_object_id(self):
        self.assertEqual("OBJECT_ID", ObjectID)

    def test_object_value(self):
        self.assertEqual("OBJECT_VALUE", ObjectValue)

    def test_row_id(self):
        self.assertEqual("ROWID", RowID)

    def test_row_num(self):
        self.assertEqual("ROWNUM", RowNum)

    def test_sys_date(self):
        self.assertEqual("SYSDATE", SysDate)

    def test_can_be_used_in_a_select_statement(self):
        query = (
            Query.from_(self.table1).where(self.table1.is_active == 1).select(PseudoColumn("abcde"))
        )

        self.assertEqual(str(query), 'SELECT abcde FROM "table1" WHERE "is_active"=1')

    def test_can_be_used_in_a_where_clause(self):
        query = (
            Query.from_(self.table1).where(PseudoColumn("abcde") > 1).select(self.table1.is_active)
        )

        self.assertEqual(str(query), 'SELECT "is_active" FROM "table1" WHERE abcde>1')

    def test_can_be_used_in_orderby(self):
        query = (
            Query.from_(self.table1)
            .select(self.table1.abcde.as_("some_name"))
            .orderby(PseudoColumn("some_name"))
        )
        self.assertEqual(str(query), 'SELECT "abcde" "some_name" FROM "table1" ORDER BY some_name')
