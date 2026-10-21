import pytest
import pytest_asyncio

from tests.testmodels import IntFields
from tortoise.exceptions import FieldError
from tortoise.expressions import Case, Expression, F, Q, ResolveContext, When
from tortoise.functions import Coalesce, Count


@pytest_asyncio.fixture
async def intfields_data(db):
    """Create IntFields test data."""
    intfields = [await IntFields.create(intnum=val) for val in range(10)]
    return intfields


@pytest.mark.asyncio
async def test_single_when(db, intfields_data):
    category = Case(When(intnum__gte=8, then="big"), default="default")
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 'big' ELSE 'default' END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN \'big\' ELSE \'default\' END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_multi_when(db, intfields_data):
    category = Case(
        When(intnum__gte=8, then="big"), When(intnum__lte=2, then="small"), default="default"
    )
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 'big' WHEN `intnum`<=2 THEN 'small' ELSE 'default' END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN \'big\' WHEN "intnum"<=2 THEN \'small\' ELSE \'default\' END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_q_object_when(db, intfields_data):
    category = Case(When(Q(intnum__gt=2, intnum__lt=8), then="middle"), default="default")
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>2 AND `intnum`<8 THEN 'middle' ELSE 'default' END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">2 AND "intnum"<8 THEN \'middle\' ELSE \'default\' END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_F_then(db, intfields_data):
    category = Case(When(intnum__gte=8, then=F("intnum_null")), default="default")
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN `intnum_null` ELSE 'default' END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN "intnum_null" ELSE \'default\' END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_AE_then(db, intfields_data):
    # AE: ArithmeticExpression
    category = Case(When(intnum__gte=8, then=F("intnum") + 1), default="default")
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN `intnum`+1 ELSE 'default' END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN "intnum"+1 ELSE \'default\' END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_func_then(db, intfields_data):
    category = Case(When(intnum__gte=8, then=Coalesce("intnum_null", 10)), default="default")
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN COALESCE(`intnum_null`,10) ELSE 'default' END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN COALESCE("intnum_null",10) ELSE \'default\' END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_F_default(db, intfields_data):
    category = Case(When(intnum__gte=8, then="big"), default=F("intnum_null"))
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 'big' ELSE `intnum_null` END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN \'big\' ELSE "intnum_null" END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_AE_default(db, intfields_data):
    # AE: ArithmeticExpression
    category = Case(When(intnum__gte=8, then=8), default=F("intnum") + 1)
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 8 ELSE `intnum`+1 END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN 8 ELSE "intnum"+1 END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_func_default(db, intfields_data):
    category = Case(When(intnum__gte=8, then=8), default=Coalesce("intnum_null", 10))
    sql = (
        IntFields.all()
        .annotate(category=category)
        .values("intnum", "category")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum`,CASE WHEN `intnum`>=8 THEN 8 ELSE COALESCE(`intnum_null`,10) END `category` FROM `intfields`"
    else:
        expected_sql = 'SELECT "intnum" "intnum",CASE WHEN "intnum">=8 THEN 8 ELSE COALESCE("intnum_null",10) END "category" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_case_when_in_where(db, intfields_data):
    category = Case(
        When(intnum__gte=8, then="big"), When(intnum__lte=2, then="small"), default="middle"
    )
    sql = (
        IntFields.all()
        .annotate(category=category)
        .filter(category__in=["big", "small"])
        .values("intnum")
        .sql(params_inline=True)
    )
    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `intnum` `intnum` FROM `intfields` WHERE CASE WHEN `intnum`>=8 THEN 'big' WHEN `intnum`<=2 THEN 'small' ELSE 'middle' END IN ('big','small')"
    else:
        expected_sql = "SELECT \"intnum\" \"intnum\" FROM \"intfields\" WHERE CASE WHEN \"intnum\">=8 THEN 'big' WHEN \"intnum\"<=2 THEN 'small' ELSE 'middle' END IN ('big','small')"
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_annotation_in_when_annotation(db, intfields_data):
    sql = (
        IntFields.all()
        .annotate(intnum_plus_1=F("intnum") + 1)
        .annotate(bigger_than_10=Case(When(Q(intnum_plus_1__gte=10), then=True), default=False))
        .values("id", "intnum", "intnum_plus_1", "bigger_than_10")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `id` `id`,`intnum` `intnum`,`intnum`+1 `intnum_plus_1`,CASE WHEN `intnum`+1>=10 THEN true ELSE false END `bigger_than_10` FROM `intfields`"
    else:
        expected_sql = 'SELECT "id" "id","intnum" "intnum","intnum"+1 "intnum_plus_1",CASE WHEN "intnum"+1>=10 THEN true ELSE false END "bigger_than_10" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_func_annotation_in_when_annotation(db, intfields_data):
    sql = (
        IntFields.all()
        .annotate(intnum_col=Coalesce("intnum", 0))
        .annotate(is_zero=Case(When(Q(intnum_col=0), then=True), default=False))
        .values("id", "intnum_col", "is_zero")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT `id` `id`,COALESCE(`intnum`,0) `intnum_col`,CASE WHEN COALESCE(`intnum`,0)=0 THEN true ELSE false END `is_zero` FROM `intfields`"
    else:
        expected_sql = 'SELECT "id" "id",COALESCE("intnum",0) "intnum_col",CASE WHEN COALESCE("intnum",0)=0 THEN true ELSE false END "is_zero" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_case_when_in_group_by(db, intfields_data):
    sql = (
        IntFields.all()
        .annotate(is_zero=Case(When(Q(intnum=0), then=True), default=False))
        .annotate(count=Count("id"))
        .group_by("is_zero")
        .values("is_zero", "count")
        .sql(params_inline=True)
    )

    dialect = db.db().schema_generator.DIALECT
    if dialect == "mysql":
        expected_sql = "SELECT CASE WHEN `intnum`=0 THEN true ELSE false END `is_zero`,COUNT(`id`) `count` FROM `intfields` GROUP BY `is_zero`"
    elif dialect == "mssql":
        expected_sql = 'SELECT CASE WHEN "intnum"=0 THEN true ELSE false END "is_zero",COUNT("id") "count" FROM "intfields" GROUP BY CASE WHEN "intnum"=0 THEN true ELSE false END'
    else:
        expected_sql = 'SELECT CASE WHEN "intnum"=0 THEN true ELSE false END "is_zero",COUNT("id") "count" FROM "intfields" GROUP BY "is_zero"'
    assert sql == expected_sql


@pytest.mark.asyncio
async def test_unknown_field_in_when_annotation(db, intfields_data):
    with pytest.raises(FieldError, match="Unknown filter param 'unknown'.+"):
        IntFields.all().annotate(intnum_col=Coalesce("intnum", 0)).annotate(
            is_zero=Case(When(Q(unknown=0), then="1"), default="2")
        ).sql(params_inline=True)


def test_invalid_args_and_unimplemented_resolve() -> None:
    msg = "expected Q objects as args"
    with pytest.raises(TypeError, match=msg):
        When(1, then="")._resolve_q_objects()  # type:ignore
    with pytest.raises(TypeError, match=msg):
        When(Q(), "s", then="")._resolve_q_objects()  # type:ignore

    msg = "expected When objects as args"
    model = IntFields
    resolve_context = ResolveContext(
        model=model,
        table=model.get_table(),
        annotations={},
        custom_filters=model._meta.filters,
    )
    with pytest.raises(TypeError, match=msg):
        Case(1).resolve(resolve_context)  # type:ignore
    with pytest.raises(TypeError, match=msg):
        Case(None).resolve(resolve_context)  # type:ignore

    with pytest.raises(NotImplementedError):
        Expression().resolve(resolve_context)

    class CustomExpression(Expression): ...

    with pytest.raises(NotImplementedError):
        CustomExpression().resolve(resolve_context)
