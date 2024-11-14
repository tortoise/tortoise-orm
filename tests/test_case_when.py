from tests.testmodels import IntFields
from tortoise import connections
from tortoise.contrib import test
from tortoise.exceptions import FieldError
from tortoise.expressions import Case, F, Q, When
from tortoise.functions import Coalesce, Count


class TestCaseWhen(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.intfields = [await IntFields.create(intnum=val) for val in range(10)]
        self.db = connections.get("models")
        self.dialect = self.db.schema_generator.DIALECT

    async def test_single_when(self):
        category = Case(When(intnum__gte=8, then="big"), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN %s ELSE %s END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN $2 ELSE $3 END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN ? ELSE ? END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_multi_when(self):
        category = Case(
            When(intnum__gte=8, then="big"), When(intnum__lte=2, then="small"), default="default"
        )
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN %s WHEN `intnum`<=%s THEN %s ELSE %s END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN $2 WHEN "intnum"<=$3 THEN $4 ELSE $5 END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN ? WHEN "intnum"<=? THEN ? ELSE ? END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_q_object_when(self):
        category = Case(When(Q(intnum__gt=2, intnum__lt=8), then="middle"), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>%s AND `intnum`<%s THEN %s ELSE %s END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">$1 AND "intnum"<$2 THEN $3 ELSE $4 END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">? AND "intnum"<? THEN ? ELSE ? END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_F_then(self):
        category = Case(When(intnum__gte=8, then=F("intnum_null")), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN `intnum_null` ELSE %s END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN "intnum_null" ELSE $2 END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN "intnum_null" ELSE ? END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_AE_then(self):
        # AE: ArithmeticExpression
        category = Case(When(intnum__gte=8, then=F("intnum") + 1), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN `intnum`+%s ELSE %s END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN "intnum"+$2 ELSE $3 END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN "intnum"+? ELSE ? END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_func_then(self):
        category = Case(When(intnum__gte=8, then=Coalesce("intnum_null", 10)), default="default")
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN COALESCE(`intnum_null`,%s) ELSE %s END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN COALESCE("intnum_null",$2) ELSE $3 END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN COALESCE("intnum_null",?) ELSE ? END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_F_default(self):
        category = Case(When(intnum__gte=8, then="big"), default=F("intnum_null"))
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN %s ELSE `intnum_null` END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN $2 ELSE "intnum_null" END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN ? ELSE "intnum_null" END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_AE_default(self):
        # AE: ArithmeticExpression
        category = Case(When(intnum__gte=8, then=8), default=F("intnum") + 1)
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN %s ELSE `intnum`+%s END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN $2 ELSE "intnum"+$3 END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN ? ELSE "intnum"+? END "category" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_func_default(self):
        category = Case(When(intnum__gte=8, then=8), default=Coalesce("intnum_null", 10))
        sql = IntFields.all().annotate(category=category).values("intnum", "category").sql()

        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=%s THEN %s ELSE COALESCE(`intnum_null`,%s) END `category` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=$1 THEN $2 ELSE COALESCE("intnum_null",$3) END "category" FROM "intfields"'
        else:
            expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=? THEN ? ELSE COALESCE("intnum_null",?) END "category" FROM "intfields"'
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
        if self.dialect == "mysql":
            expected_sql = "SELECT `intnum` `intnum` FROM `intfields` WHERE CASE WHEN `intnum`>=%s THEN %s WHEN `intnum`<=%s THEN %s ELSE %s END IN (%s,%s)"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "intnum" "intnum" FROM "intfields" WHERE CASE WHEN "intnum">=$1 THEN $2 WHEN "intnum"<=$3 THEN $4 ELSE $5 END IN ($6,$7)'
        else:
            expected_sql = 'SELECT "intnum" "intnum" FROM "intfields" WHERE CASE WHEN "intnum">=? THEN ? WHEN "intnum"<=? THEN ? ELSE ? END IN (?,?)'
        self.assertEqual(sql, expected_sql)

    async def test_annotation_in_when_annotation(self):
        sql = (
            IntFields.all()
            .annotate(intnum_plus_1=F("intnum") + 1)
            .annotate(bigger_than_10=Case(When(Q(intnum_plus_1__gte=10), then=True), default=False))
            .values("id", "intnum", "intnum_plus_1", "bigger_than_10")
            .sql()
        )

        if self.dialect == "mysql":
            expected_sql = "SELECT `id` `id`,`intnum` `intnum`,`intnum`+%s `intnum_plus_1`,CASE WHEN `intnum`+%s>=%s THEN %s ELSE %s END `bigger_than_10` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "id" "id","intnum" "intnum","intnum"+$1 "intnum_plus_1",CASE WHEN "intnum"+$2>=$3 THEN $4 ELSE $5 END "bigger_than_10" FROM "intfields"'
        else:
            expected_sql = 'SELECT "id" "id","intnum" "intnum","intnum"+? "intnum_plus_1",CASE WHEN "intnum"+?>=? THEN ? ELSE ? END "bigger_than_10" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_func_annotation_in_when_annotation(self):
        sql = (
            IntFields.all()
            .annotate(intnum_col=Coalesce("intnum", 0))
            .annotate(is_zero=Case(When(Q(intnum_col=0), then=True), default=False))
            .values("id", "intnum_col", "is_zero")
            .sql()
        )

        if self.dialect == "mysql":
            expected_sql = "SELECT `id` `id`,COALESCE(`intnum`,%s) `intnum_col`,CASE WHEN COALESCE(`intnum`,%s)=%s THEN %s ELSE %s END `is_zero` FROM `intfields`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT "id" "id",COALESCE("intnum",$1) "intnum_col",CASE WHEN COALESCE("intnum",$2)=$3 THEN $4 ELSE $5 END "is_zero" FROM "intfields"'
        else:
            expected_sql = 'SELECT "id" "id",COALESCE("intnum",?) "intnum_col",CASE WHEN COALESCE("intnum",?)=? THEN ? ELSE ? END "is_zero" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    async def test_case_when_in_group_by(self):
        sql = (
            IntFields.all()
            .annotate(is_zero=Case(When(Q(intnum=0), then=True), default=False))
            .annotate(count=Count("id"))
            .group_by("is_zero")
            .values("is_zero", "count")
            .sql()
        )

        if self.dialect == "mysql":
            expected_sql = "SELECT CASE WHEN `intnum`=%s THEN %s ELSE %s END `is_zero`,COUNT(`id`) `count` FROM `intfields` GROUP BY `is_zero`"
        elif self.dialect == "postgres":
            expected_sql = 'SELECT CASE WHEN "intnum"=$1 THEN $2 ELSE $3 END "is_zero",COUNT("id") "count" FROM "intfields" GROUP BY "is_zero"'
        elif self.dialect == "mssql":
            expected_sql = 'SELECT CASE WHEN "intnum"=? THEN ? ELSE ? END "is_zero",COUNT("id") "count" FROM "intfields" GROUP BY CASE WHEN "intnum"=? THEN ? ELSE ? END'
        else:
            expected_sql = 'SELECT CASE WHEN "intnum"=? THEN ? ELSE ? END "is_zero",COUNT("id") "count" FROM "intfields" GROUP BY "is_zero"'
        self.assertEqual(sql, expected_sql)

    async def test_unknown_field_in_when_annotation(self):
        with self.assertRaisesRegex(FieldError, "Unknown filter param 'unknown'.+"):
            IntFields.all().annotate(intnum_col=Coalesce("intnum", 0)).annotate(
                is_zero=Case(When(Q(unknown=0), then="1"), default="2")
            ).sql()
