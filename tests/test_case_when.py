from tests.testmodels import IntFields
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.expressions import F
from tortoise.functions import Case, Coalesce, When
from tortoise.query_utils import Q


class TestCaseWhen(test.TestCase):
    async def setUp(self):
        self.intfields = [await IntFields.create(intnum=val) for val in range(10)]
        self.db = Tortoise.get_connection("models")

    async def test_single_when(self):
        category = Case(When(intnum__gte=8, then="big"), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 'big' ELSE 'default' END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN \'big\' ELSE \'default\' END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_multi_when(self):
        category = Case(
            When(intnum__gte=8, then="big"), When(intnum__lte=2, then="small"), default="default"
        )
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 'big' WHEN `intnum`<=2 THEN 'small' ELSE 'default' END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN \'big\' WHEN "intnum"<=2 THEN \'small\' ELSE \'default\' END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_q_object_when(self):
        category = Case(When(Q(intnum__gt=2, intnum__lt=8), then="middle"), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>2 AND `intnum`<8 THEN 'middle' ELSE 'default' END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">2 AND "intnum"<8 THEN \'middle\' ELSE \'default\' END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_F_then(self):
        category = Case(When(intnum__gte=8, then=F("intnum_null")), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN `intnum_null` ELSE 'default' END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN "intnum_null" ELSE \'default\' END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_AE_then(self):
        # AE: ArithmeticExpression
        category = Case(When(intnum__gte=8, then=F("intnum") + 1), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN `intnum`+1 ELSE 'default' END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN "intnum"+1 ELSE \'default\' END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_func_then(self):
        category = Case(When(intnum__gte=8, then=Coalesce("intnum_null", 10)), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN COALESCE(`intnum_null`,10) ELSE 'default' END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN COALESCE("intnum_null",10) ELSE \'default\' END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_F_default(self):
        category = Case(When(intnum__gte=8, then="big"), default=F("intnum_null"))
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 'big' ELSE `intnum_null` END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN \'big\' ELSE "intnum_null" END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_AE_default(self):
        # AE: ArithmeticExpression
        category = Case(When(intnum__gte=8, then=8), default=F("intnum") + 1)
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 8 ELSE `intnum`+1 END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN 8 ELSE "intnum"+1 END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_func_default(self):
        category = Case(When(intnum__gte=8, then=8), default=Coalesce("intnum_null", 10))
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 8 ELSE COALESCE(`intnum_null`,10) END `category` FROM `intfields`"
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN 8 ELSE COALESCE("intnum_null",10) END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_case_when_in_where(self):
        category = Case(
            When(intnum__gte=8, then="big"), When(intnum__lte=2, then="small"), default="middle"
        )
        sql = (
            IntFields.all()
            .annotate(category=category)
            .filter(category__in=["big", "small"])
            .values("intnum")
            .sql()
        )
        dialect = self.db.schema_generator.DIALECT
        if dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum` FROM `intfields` WHERE CASE WHEN `intnum`>=8 THEN 'big' WHEN `intnum`<=2 THEN 'small' ELSE 'middle' END IN ('big','small')"
        else:
            expected_sql = "SELECT \"intnum\" \"intnum\" FROM \"intfields\" WHERE CASE WHEN \"intnum\">=8 THEN 'big' WHEN \"intnum\"<=2 THEN 'small' ELSE 'middle' END IN ('big','small')"
        self.assertEqual(sql, expected_sql)
