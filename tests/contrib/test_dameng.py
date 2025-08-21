"""
Test Dameng contrib module
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from tortoise.contrib.dameng.fields import IntervalField, RowIDField, XMLField
from tortoise.contrib.dameng.functions import (
    Decode,
    InitCap,
    Instr,
    ListAgg,
    LPad,
    NVL,
    RPad,
    RowNum,
    SysDate,
    ToChar,
    ToDate,
)
from tortoise.expressions import F, Q


class TestDamengFields(unittest.TestCase):
    """Test Dameng-specific field definitions"""

    def test_xml_field_init(self):
        """Test XMLField initialization"""
        field = XMLField()
        self.assertEqual(field.field_type, str)
        self.assertEqual(field.SQL_TYPE, "XMLTYPE")

    def test_interval_field_init(self):
        """Test IntervalField initialization"""
        field = IntervalField()
        self.assertEqual(field.field_type, str)
        self.assertEqual(field.interval_type, "DAY TO SECOND")

    def test_rowid_field_init(self):
        """Test RowIDField initialization"""
        field = RowIDField()
        self.assertEqual(field.field_type, str)
        self.assertEqual(field.SQL_TYPE, "ROWID")
        self.assertTrue(field.generated)

    def test_xml_field_to_db_value(self):
        """Test XMLField to_db_value"""
        field = XMLField()
        xml_str = '<root><item>test</item></root>'
        self.assertEqual(field.to_db_value(xml_str, None), xml_str)
        self.assertIsNone(field.to_db_value(None, None))

    def test_interval_field_to_db_value(self):
        """Test IntervalField to_db_value"""
        field = IntervalField()
        interval = "1 02:30:00"  # 1 day, 2 hours, 30 minutes
        # Should return string as is
        self.assertEqual(field.to_db_value(interval, None), "1 02:30:00")
        self.assertIsNone(field.to_db_value(None, None))

    def test_interval_field_to_python_value(self):
        """Test IntervalField to_python_value"""
        field = IntervalField()
        # Test with interval string
        interval_str = "1 02:03:00"  # 1 day, 2 hours, 3 minutes
        result = field.to_python_value(interval_str)
        self.assertEqual(result, "1 02:03:00")
        
        # Test with None
        self.assertIsNone(field.to_python_value(None))


class TestDamengFunctions(unittest.TestCase):
    """Test Dameng-specific SQL functions"""

    def test_tochar_function(self):
        """Test ToChar function creation"""
        func = ToChar("created_at", "YYYY-MM-DD")
        self.assertEqual(func.name, "TO_CHAR")
        
        # Test with field reference
        func = ToChar(F("created_at"), "DD/MM/YYYY")
        self.assertEqual(func.name, "TO_CHAR")

    def test_todate_function(self):
        """Test ToDate function creation"""
        func = ToDate("2024-01-01", "YYYY-MM-DD")
        self.assertEqual(func.name, "TO_DATE")

    def test_sysdate_function(self):
        """Test SysDate function creation"""
        func = SysDate()
        self.assertEqual(func.name, "SYSDATE")

    def test_initcap_function(self):
        """Test InitCap function creation"""
        func = InitCap("name")
        self.assertEqual(func.name, "INITCAP")
        
        # Test with field reference
        func = InitCap(F("title"))
        self.assertEqual(func.name, "INITCAP")

    def test_instr_function(self):
        """Test Instr function creation"""
        func = Instr("email", "@")
        self.assertEqual(func.name, "INSTR")
        
        # Test with optional parameters
        func = Instr("text", "search", 1, 1)
        self.assertEqual(func.name, "INSTR")

    def test_lpad_function(self):
        """Test LPad function creation"""
        func = LPad("id", 5, "0")
        self.assertEqual(func.name, "LPAD")
        
        # Test with field reference
        func = LPad(F("code"), 10, "X")
        self.assertEqual(func.name, "LPAD")

    def test_rpad_function(self):
        """Test RPad function creation"""
        func = RPad("name", 20, " ")
        self.assertEqual(func.name, "RPAD")

    def test_nvl_function(self):
        """Test NVL function creation"""
        func = NVL("status", "active")
        self.assertEqual(func.name, "NVL")
        
        # Test with field references
        func = NVL(F("status"), F("default_status"))
        self.assertEqual(func.name, "NVL")

    def test_decode_function(self):
        """Test Decode function creation"""
        func = Decode("type", 1, "A", 2, "B", "C")
        self.assertEqual(func.name, "DECODE")
        
        # Test with multiple pairs
        func = Decode(F("category"), "1", "Basic", "2", "Premium", "Unknown")
        self.assertEqual(func.name, "DECODE")

    def test_rownum_function(self):
        """Test RowNum function creation"""
        func = RowNum()
        self.assertEqual(func.name, "ROWNUM")

    def test_listagg_function(self):
        """Test ListAgg function creation"""
        func = ListAgg("name", ",")
        self.assertEqual(func.name, "LISTAGG")
        
        # Test with order by
        func = ListAgg(F("name"), " | ", F("created_at"))
        self.assertEqual(func.name, "LISTAGG")

    def test_function_combinations(self):
        """Test combining multiple functions"""
        # NVL with ToChar
        func = NVL(ToChar("date", "YYYY-MM-DD"), "N/A")
        self.assertEqual(func.name, "NVL")
        
        # InitCap with NVL
        func = InitCap(NVL("name", "unnamed"))
        self.assertEqual(func.name, "INITCAP")

    def test_function_in_expressions(self):
        """Test functions in query expressions"""
        # In Q objects
        q = Q(status=NVL(F("status"), "active"))
        self.assertIsInstance(q, Q)
        
        # Functions can be used in expressions
        func = RowNum()
        self.assertEqual(func.name, "ROWNUM")