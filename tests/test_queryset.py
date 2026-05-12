import pytest
import pytest_asyncio

from tests.testmodels import (
    Author,
    Book,
    Event,
    IntFields,
    MinRelation,
    Node,
    Reporter,
    Tournament,
    Tree,
)
from tortoise import connections
from tortoise.backends.psycopg.client import PsycopgClient
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ
from tortoise.exceptions import (
    DoesNotExist,
    FieldError,
    IntegrityError,
    MultipleObjectsReturned,
    NotExistOrMultiple,
    ParamsError,
)
from tortoise.expressions import F, RawSQL, Subquery, Value
from tortoise.functions import Avg

# TODO: Test the many exceptions in QuerySet
# TODO: .filter(intnum_null=None) does not work as expected


@pytest_asyncio.fixture
async def intfields_data(db):
    """Build large dataset for IntFields tests."""
    intfields = [await IntFields.create(intnum=val) for val in range(10, 100, 3)]
    return intfields


@pytest.mark.asyncio
async def test_all_count(db, intfields_data):
    assert await IntFields.all().count() == 30
    assert await IntFields.filter(intnum_null=80).count() == 0


@pytest.mark.asyncio
async def test_exists(db, intfields_data):
    ret = await IntFields.filter(intnum=0).exists()
    assert not ret

    ret = await IntFields.filter(intnum=10).exists()
    assert ret

    ret = await IntFields.filter(intnum__gt=10).exists()
    assert ret

    ret = await IntFields.filter(intnum__lt=10).exists()
    assert not ret


@pytest.mark.asyncio
async def test_limit_count(db, intfields_data):
    assert await IntFields.all().limit(10).count() == 10


@pytest.mark.asyncio
async def test_limit_negative(db, intfields_data):
    with pytest.raises(ParamsError, match="Limit should be non-negative number"):
        await IntFields.all().limit(-10)


@requireCapability(dialect="sqlite")
@pytest.mark.asyncio
async def test_limit_zero(db, intfields_data):
    sql = IntFields.all().only("id").limit(0).sql()
    assert sql == 'SELECT "id" "id" FROM "intfields" LIMIT ?'


@pytest.mark.asyncio
async def test_offset_count(db, intfields_data):
    assert await IntFields.all().offset(10).count() == 20


@pytest.mark.asyncio
async def test_offset_negative(db, intfields_data):
    with pytest.raises(ParamsError, match="Offset should be non-negative number"):
        await IntFields.all().offset(-10)


@pytest.mark.asyncio
async def test_slicing_start_and_stop(db, intfields_data):
    sliced_queryset = IntFields.all().order_by("intnum")[1:5]
    manually_sliced_queryset = IntFields.all().order_by("intnum").offset(1).limit(4)
    assert list(await sliced_queryset) == list(await manually_sliced_queryset)


@pytest.mark.asyncio
async def test_slicing_only_limit(db, intfields_data):
    sliced_queryset = IntFields.all().order_by("intnum")[:5]
    manually_sliced_queryset = IntFields.all().order_by("intnum").limit(5)
    assert list(await sliced_queryset) == list(await manually_sliced_queryset)


@pytest.mark.asyncio
async def test_slicing_only_offset(db, intfields_data):
    sliced_queryset = IntFields.all().order_by("intnum")[5:]
    manually_sliced_queryset = IntFields.all().order_by("intnum").offset(5)
    assert list(await sliced_queryset) == list(await manually_sliced_queryset)


@pytest.mark.asyncio
async def test_slicing_count(db, intfields_data):
    queryset = IntFields.all().order_by("intnum")[1:5]
    assert await queryset.count() == 4


def test_slicing_negative_values(db):
    with pytest.raises(
        ParamsError,
        match="Slice start should be non-negative number or None.",
    ):
        _ = IntFields.all()[-1:]

    with pytest.raises(
        ParamsError,
        match="Slice stop should be non-negative number greater that slice start, or None.",
    ):
        _ = IntFields.all()[:-1]


def test_slicing_stop_before_start(db):
    with pytest.raises(
        ParamsError,
        match="Slice stop should be non-negative number greater that slice start, or None.",
    ):
        _ = IntFields.all()[2:1]


@pytest.mark.asyncio
async def test_slicing_steps(db, intfields_data):
    sliced_queryset = IntFields.all().order_by("intnum")[::1]
    manually_sliced_queryset = IntFields.all().order_by("intnum")
    assert list(await sliced_queryset) == list(await manually_sliced_queryset)

    with pytest.raises(
        ParamsError,
        match="Slice steps should be 1 or None.",
    ):
        _ = IntFields.all()[::2]


@pytest.mark.asyncio
async def test_join_count(db):
    tour = await Tournament.create(name="moo")
    await MinRelation.create(tournament=tour)

    assert await MinRelation.all().count() == 1
    assert await MinRelation.filter(tournament__id=tour.id).count() == 1


@pytest.mark.asyncio
async def test_modify_dataset(db, intfields_data):
    # Modify dataset
    rows_affected = await IntFields.filter(intnum__gte=70).update(intnum_null=80)
    assert rows_affected == 10
    assert await IntFields.filter(intnum_null=80).count() == 10
    assert await IntFields.filter(intnum_null__isnull=True).count() == 20
    await IntFields.filter(intnum_null__isnull=True).update(intnum_null=-1)
    assert await IntFields.filter(intnum_null=None).count() == 0
    assert await IntFields.filter(intnum_null=-1).count() == 20


@pytest.mark.asyncio
async def test_distinct(db, intfields_data):
    # Test distinct
    await IntFields.filter(intnum__gte=70).update(intnum_null=80)
    await IntFields.filter(intnum_null__isnull=True).update(intnum_null=-1)

    assert await IntFields.all().order_by("intnum_null").distinct().values_list(
        "intnum_null", flat=True
    ) == [-1, 80]

    assert await IntFields.all().order_by("intnum_null").distinct().values("intnum_null") == [
        {"intnum_null": -1},
        {"intnum_null": 80},
    ]


@pytest.mark.asyncio
async def test_limit_offset_values_list(db, intfields_data):
    # Test limit/offset/ordering values_list
    assert await IntFields.all().order_by("intnum").limit(10).values_list("intnum", flat=True) == [
        10,
        13,
        16,
        19,
        22,
        25,
        28,
        31,
        34,
        37,
    ]

    assert await IntFields.all().order_by("intnum").limit(10).offset(10).values_list(
        "intnum", flat=True
    ) == [40, 43, 46, 49, 52, 55, 58, 61, 64, 67]

    assert await IntFields.all().order_by("intnum").limit(10).offset(20).values_list(
        "intnum", flat=True
    ) == [70, 73, 76, 79, 82, 85, 88, 91, 94, 97]

    assert (
        await IntFields.all()
        .order_by("intnum")
        .limit(10)
        .offset(30)
        .values_list("intnum", flat=True)
        == []
    )

    assert await IntFields.all().order_by("-intnum").limit(10).values_list("intnum", flat=True) == [
        97,
        94,
        91,
        88,
        85,
        82,
        79,
        76,
        73,
        70,
    ]

    assert await IntFields.all().order_by("intnum").limit(10).filter(intnum__gte=40).values_list(
        "intnum", flat=True
    ) == [40, 43, 46, 49, 52, 55, 58, 61, 64, 67]


@pytest.mark.asyncio
async def test_limit_offset_values(db, intfields_data):
    # Test limit/offset/ordering values
    assert await IntFields.all().order_by("intnum").limit(5).values("intnum") == [
        {"intnum": 10},
        {"intnum": 13},
        {"intnum": 16},
        {"intnum": 19},
        {"intnum": 22},
    ]

    assert await IntFields.all().order_by("intnum").limit(5).offset(10).values("intnum") == [
        {"intnum": 40},
        {"intnum": 43},
        {"intnum": 46},
        {"intnum": 49},
        {"intnum": 52},
    ]

    assert await IntFields.all().order_by("intnum").limit(5).offset(30).values("intnum") == []

    assert await IntFields.all().order_by("-intnum").limit(5).values("intnum") == [
        {"intnum": 97},
        {"intnum": 94},
        {"intnum": 91},
        {"intnum": 88},
        {"intnum": 85},
    ]

    assert await IntFields.all().order_by("intnum").limit(5).filter(intnum__gte=40).values(
        "intnum"
    ) == [
        {"intnum": 40},
        {"intnum": 43},
        {"intnum": 46},
        {"intnum": 49},
        {"intnum": 52},
    ]


@pytest.mark.asyncio
async def test_in_bulk(db, intfields_data):
    id_list = [item.pk for item in await IntFields.all().only("id").limit(2)]
    ret = await IntFields.in_bulk(id_list=id_list)
    assert list(ret.keys()) == id_list


@pytest.mark.asyncio
async def test_first(db, intfields_data):
    # Test first
    assert (await IntFields.all().order_by("intnum").filter(intnum__gte=40).first()).intnum == 40
    assert (await IntFields.all().order_by("intnum").filter(intnum__gte=40).first().values())[
        "intnum"
    ] == 40
    assert (await IntFields.all().order_by("intnum").filter(intnum__gte=40).first().values_list())[
        1
    ] == 40

    assert await IntFields.all().order_by("intnum").filter(intnum__gte=400).first() is None
    assert await IntFields.all().order_by("intnum").filter(intnum__gte=400).first().values() is None
    assert (
        await IntFields.all().order_by("intnum").filter(intnum__gte=400).first().values_list()
        is None
    )


@pytest.mark.asyncio
async def test_last(db, intfields_data):
    assert (await IntFields.all().order_by("intnum").filter(intnum__gte=40).last()).intnum == 97
    assert (await IntFields.all().order_by("intnum").filter(intnum__gte=40).last().values())[
        "intnum"
    ] == 97
    assert (await IntFields.all().order_by("intnum").filter(intnum__gte=40).last().values_list())[
        1
    ] == 97

    assert await IntFields.all().order_by("intnum").filter(intnum__gte=400).last() is None
    assert await IntFields.all().order_by("intnum").filter(intnum__gte=400).last().values() is None
    assert (
        await IntFields.all().order_by("intnum").filter(intnum__gte=400).last().values_list()
        is None
    )
    assert (await IntFields.all().filter(intnum__gte=40).last()).intnum == 97


@pytest.mark.asyncio
async def test_latest(db, intfields_data):
    assert (await IntFields.all().latest("intnum")).intnum == 97
    assert (await IntFields.all().order_by("-intnum").first()).intnum == (
        await IntFields.all().latest("intnum")
    ).intnum
    assert (await IntFields.all().filter(intnum__gte=40).latest("intnum")).intnum == 97
    assert (await IntFields.all().filter(intnum__gte=40).latest("intnum").values())["intnum"] == 97
    assert (await IntFields.all().filter(intnum__gte=40).latest("intnum").values_list())[1] == 97

    assert await IntFields.all().filter(intnum__gte=400).latest("intnum") is None
    assert await IntFields.all().filter(intnum__gte=400).latest("intnum").values() is None
    assert await IntFields.all().filter(intnum__gte=400).latest("intnum").values_list() is None

    with pytest.raises(FieldError):
        await IntFields.all().latest()

    with pytest.raises(FieldError):
        await IntFields.all().latest("some_unkown_field")


@pytest.mark.asyncio
async def test_earliest(db, intfields_data):
    assert (await IntFields.all().earliest("intnum")).intnum == 10
    assert (await IntFields.all().order_by("intnum").first()).intnum == (
        await IntFields.all().earliest("intnum")
    ).intnum
    assert (await IntFields.all().filter(intnum__gte=40).earliest("intnum")).intnum == 40
    assert (await IntFields.all().filter(intnum__gte=40).earliest("intnum").values())[
        "intnum"
    ] == 40
    assert (await IntFields.all().filter(intnum__gte=40).earliest("intnum").values_list())[1] == 40

    assert await IntFields.all().filter(intnum__gte=400).earliest("intnum") is None
    assert await IntFields.all().filter(intnum__gte=400).earliest("intnum").values() is None
    assert await IntFields.all().filter(intnum__gte=400).earliest("intnum").values_list() is None

    with pytest.raises(FieldError):
        await IntFields.all().earliest()

    with pytest.raises(FieldError):
        await IntFields.all().earliest("some_unkown_field")


@pytest.mark.asyncio
async def test_get_or_none(db, intfields_data):
    assert (await IntFields.all().get_or_none(intnum=40)).intnum == 40
    assert (await IntFields.all().get_or_none(intnum=40).values())["intnum"] == 40
    assert (await IntFields.all().get_or_none(intnum=40).values_list())[1] == 40

    assert await IntFields.all().order_by("intnum").get_or_none(intnum__gte=400) is None

    assert await IntFields.all().order_by("intnum").get_or_none(intnum__gte=400).values() is None

    assert (
        await IntFields.all().order_by("intnum").get_or_none(intnum__gte=400).values_list() is None
    )

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.all().order_by("intnum").get_or_none(intnum__gte=40)

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.all().order_by("intnum").get_or_none(intnum__gte=40).values()

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.all().order_by("intnum").get_or_none(intnum__gte=40).values_list()


@pytest.mark.asyncio
async def test_get(db, intfields_data):
    await IntFields.filter(intnum__gte=70).update(intnum_null=80)

    # Test get
    assert (await IntFields.all().get(intnum=40)).intnum == 40
    assert (await IntFields.all().get(intnum=40).values())["intnum"] == 40
    assert (await IntFields.all().get(intnum=40).values_list())[1] == 40

    assert (await IntFields.all().all().all().all().all().get(intnum=40)).intnum == 40
    assert (await IntFields.all().all().all().all().all().get(intnum=40).values())["intnum"] == 40
    assert (await IntFields.all().all().all().all().all().get(intnum=40).values_list())[1] == 40

    assert (await IntFields.get(intnum=40)).intnum == 40
    assert (await IntFields.get(intnum=40).values())["intnum"] == 40
    assert (await IntFields.get(intnum=40).values_list())[1] == 40

    with pytest.raises(DoesNotExist):
        await IntFields.all().get(intnum=41)

    with pytest.raises(DoesNotExist):
        await IntFields.all().get(intnum=41).values()

    with pytest.raises(DoesNotExist):
        await IntFields.all().get(intnum=41).values_list()

    with pytest.raises(DoesNotExist):
        await IntFields.get(intnum=41)

    with pytest.raises(DoesNotExist):
        await IntFields.get(intnum=41).values()

    with pytest.raises(DoesNotExist):
        await IntFields.get(intnum=41).values_list()

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.all().get(intnum_null=80)

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.all().get(intnum_null=80).values()

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.all().get(intnum_null=80).values_list()

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.get(intnum_null=80)

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.get(intnum_null=80).values()

    with pytest.raises(MultipleObjectsReturned):
        await IntFields.get(intnum_null=80).values_list()


@pytest.mark.asyncio
async def test_delete(db, intfields_data):
    # Test delete
    await (await IntFields.get(intnum=40)).delete()

    with pytest.raises(DoesNotExist):
        await IntFields.get(intnum=40)

    assert await IntFields.all().count() == 29

    rows_affected = (
        await IntFields.all().order_by("intnum").limit(10).filter(intnum__gte=70).delete()
    )
    assert rows_affected == 10

    assert await IntFields.all().count() == 19


@requireCapability(support_update_limit_order_by=True)
@pytest.mark.asyncio
async def test_delete_limit(db, intfields_data):
    await IntFields.all().limit(1).delete()
    assert await IntFields.all().count() == 29


@requireCapability(support_update_limit_order_by=True)
@pytest.mark.asyncio
async def test_delete_limit_order_by(db, intfields_data):
    await IntFields.all().limit(1).order_by("-id").delete()
    assert await IntFields.all().count() == 29
    with pytest.raises(DoesNotExist):
        await IntFields.get(intnum=97)


@pytest.mark.asyncio
async def test_async_iter(db, intfields_data):
    counter = 0
    async for _ in IntFields.all():
        counter += 1

    assert await IntFields.all().count() == counter


@pytest.mark.asyncio
async def test_update_basic(db):
    obj0 = await IntFields.create(intnum=2147483647)
    await IntFields.filter(id=obj0.id).update(intnum=2147483646)
    obj = await IntFields.get(id=obj0.id)
    assert obj.intnum == 2147483646
    assert obj.intnum_null is None


@pytest.mark.asyncio
async def test_update_f_expression(db):
    obj0 = await IntFields.create(intnum=2147483647)
    await IntFields.filter(id=obj0.id).update(intnum=F("intnum") - 1)
    obj = await IntFields.get(id=obj0.id)
    assert obj.intnum == 2147483646


@pytest.mark.asyncio
async def test_update_badparam(db):
    obj0 = await IntFields.create(intnum=2147483647)
    with pytest.raises(FieldError, match="Unknown keyword argument"):
        await IntFields.filter(id=obj0.id).update(badparam=1)


@pytest.mark.asyncio
async def test_update_pk(db):
    obj0 = await IntFields.create(intnum=2147483647)
    with pytest.raises(IntegrityError, match="is PK and can not be updated"):
        await IntFields.filter(id=obj0.id).update(id=1)


@pytest.mark.asyncio
async def test_update_virtual(db):
    tour = await Tournament.create(name="moo")
    obj0 = await MinRelation.create(tournament=tour)
    with pytest.raises(FieldError, match="is virtual and can not be updated"):
        await MinRelation.filter(id=obj0.id).update(participants=[])


@pytest.mark.asyncio
async def test_bad_ordering(db, intfields_data):
    with pytest.raises(FieldError, match="Unknown field moo1fip for model IntFields"):
        await IntFields.all().order_by("moo1fip")


@pytest.mark.asyncio
async def test_duplicate_values(db, intfields_data):
    with pytest.raises(FieldError, match="Duplicate key intnum"):
        await IntFields.all().values("intnum", "intnum")


@pytest.mark.asyncio
async def test_duplicate_values_list(db, intfields_data):
    await IntFields.all().values_list("intnum", "intnum")


@pytest.mark.asyncio
async def test_duplicate_values_kw(db, intfields_data):
    with pytest.raises(FieldError, match="Duplicate key intnum"):
        await IntFields.all().values("intnum", intnum="intnum_null")


@pytest.mark.asyncio
async def test_duplicate_values_kw_badmap(db, intfields_data):
    with pytest.raises(FieldError, match='Unknown field "intnum2" for model "IntFields"'):
        await IntFields.all().values(intnum="intnum2")


@pytest.mark.asyncio
async def test_bad_values(db, intfields_data):
    with pytest.raises(FieldError, match='Unknown field "int2num" for model "IntFields"'):
        await IntFields.all().values("int2num")


@pytest.mark.asyncio
async def test_bad_values_list(db, intfields_data):
    with pytest.raises(FieldError, match='Unknown field "int2num" for model "IntFields"'):
        await IntFields.all().values_list("int2num")


@pytest.mark.asyncio
async def test_many_flat_values_list(db, intfields_data):
    with pytest.raises(TypeError, match="You can flat value_list only if contains one field"):
        await IntFields.all().values_list("intnum", "intnum_null", flat=True)


@pytest.mark.asyncio
async def test_all_flat_values_list(db, intfields_data):
    with pytest.raises(TypeError, match="You can flat value_list only if contains one field"):
        await IntFields.all().values_list(flat=True)


@pytest.mark.asyncio
async def test_all_values_list(db, intfields_data):
    data = await IntFields.all().order_by("id").values_list()
    assert data[2] == (intfields_data[2].id, 16, None)


@pytest.mark.asyncio
async def test_all_values(db, intfields_data):
    data = await IntFields.all().order_by("id").values()
    assert data[2] == {"id": intfields_data[2].id, "intnum": 16, "intnum_null": None}


@pytest.mark.asyncio
async def test_order_by_bad_value(db, intfields_data):
    with pytest.raises(FieldError, match="Unknown field badid for model IntFields"):
        await IntFields.all().order_by("badid").values_list()


@pytest.mark.asyncio
async def test_annotate_order_expression(db, intfields_data):
    data = (
        await IntFields.annotate(idp=F("id") + 1).order_by("-idp").first().values_list("id", "idp")
    )
    assert data[0] + 1 == data[1]


@pytest.mark.asyncio
async def test_annotate_order_rawsql(db, intfields_data):
    qs = IntFields.annotate(idp=RawSQL("id+1")).order_by("-idp")
    data = await qs.first().values_list("id", "idp")
    assert data[0] + 1 == data[1]


@pytest.mark.asyncio
async def test_annotate_expression_filter(db, intfields_data):
    count = await IntFields.annotate(intnum1=F("intnum") + 1).filter(intnum1__gt=30).count()
    assert count == 23


@pytest.mark.asyncio
async def test_get_raw_sql(db, intfields_data):
    sql = IntFields.all().sql()
    assert "SELECT" in sql and "FROM" in sql


@requireCapability(support_index_hint=True)
@pytest.mark.asyncio
async def test_force_index(db, intfields_data):
    sql = IntFields.filter(pk=1).only("id").force_index("index_name").sql()
    assert sql == "SELECT `id` `id` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s"

    sql_again = IntFields.filter(pk=1).only("id").force_index("index_name").sql()
    assert sql_again == "SELECT `id` `id` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s"


@requireCapability(support_index_hint=True)
@pytest.mark.asyncio
async def test_force_index_available_in_more_query(db, intfields_data):
    sql_ValuesQuery = IntFields.filter(pk=1).force_index("index_name").values("id").sql()
    assert (
        sql_ValuesQuery
        == "SELECT `id` `id` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s"
    )

    sql_ValuesListQuery = IntFields.filter(pk=1).force_index("index_name").values_list("id").sql()
    assert (
        sql_ValuesListQuery
        == "SELECT `id` `0` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s"
    )

    sql_CountQuery = IntFields.filter(pk=1).force_index("index_name").count().sql()
    assert (
        sql_CountQuery
        == "SELECT COUNT(*) FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s"
    )

    sql_ExistsQuery = IntFields.filter(pk=1).force_index("index_name").exists().sql()
    assert (
        sql_ExistsQuery
        == "SELECT 1 FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s LIMIT %s"
    )


@requireCapability(support_index_hint=True)
@pytest.mark.asyncio
async def test_use_index(db, intfields_data):
    sql = IntFields.filter(pk=1).only("id").use_index("index_name").sql()
    assert sql == "SELECT `id` `id` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s"

    sql_again = IntFields.filter(pk=1).only("id").use_index("index_name").sql()
    assert sql_again == "SELECT `id` `id` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s"


@requireCapability(support_index_hint=True)
@pytest.mark.asyncio
async def test_use_index_available_in_more_query(db, intfields_data):
    sql_ValuesQuery = IntFields.filter(pk=1).use_index("index_name").values("id").sql()
    assert (
        sql_ValuesQuery
        == "SELECT `id` `id` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s"
    )

    sql_ValuesListQuery = IntFields.filter(pk=1).use_index("index_name").values_list("id").sql()
    assert (
        sql_ValuesListQuery
        == "SELECT `id` `0` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s"
    )

    sql_CountQuery = IntFields.filter(pk=1).use_index("index_name").count().sql()
    assert (
        sql_CountQuery == "SELECT COUNT(*) FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s"
    )

    sql_ExistsQuery = IntFields.filter(pk=1).use_index("index_name").exists().sql()
    assert (
        sql_ExistsQuery
        == "SELECT 1 FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s LIMIT %s"
    )


@requireCapability(support_for_update=True)
@pytest.mark.asyncio
async def test_select_for_update(db, intfields_data):
    sql1 = IntFields.filter(pk=1).only("id").select_for_update().sql()
    sql2 = IntFields.filter(pk=1).only("id").select_for_update(nowait=True).sql()
    sql3 = IntFields.filter(pk=1).only("id").select_for_update(skip_locked=True).sql()
    sql4 = IntFields.filter(pk=1).only("id").select_for_update(of=("intfields",)).sql()
    sql5 = IntFields.filter(pk=1).only("id").select_for_update(no_key=True).sql()

    db_conn = connections.get("models")
    dialect = db_conn.schema_generator.DIALECT
    if dialect == "postgres":
        if isinstance(db_conn, PsycopgClient):
            assert sql1 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE'
            assert sql2 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE NOWAIT'
            assert sql3 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE SKIP LOCKED'
            assert (
                sql4 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE OF "intfields"'
            )
            assert sql5 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR NO KEY UPDATE'
        else:
            assert sql1 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE'
            assert sql2 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE NOWAIT'
            assert sql3 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE SKIP LOCKED'
            assert (
                sql4 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE OF "intfields"'
            )
            assert sql5 == 'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR NO KEY UPDATE'
    elif dialect == "mysql":
        assert sql1 == "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE"
        assert sql2 == "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE NOWAIT"
        assert sql3 == "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE SKIP LOCKED"
        assert sql4 == "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE OF `intfields`"
        assert sql5 == "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE"


@pytest.mark.asyncio
async def test_select_related(db):
    tournament = await Tournament.create(name="1")
    reporter = await Reporter.create(name="Reporter")
    event = await Event.create(name="1", tournament=tournament, reporter=reporter)
    event = await Event.all().select_related("tournament", "reporter").get(pk=event.pk)
    assert event.tournament.pk == tournament.pk
    assert event.reporter.pk == reporter.pk


@pytest.mark.asyncio
async def test_select_related_with_two_same_models(db):
    parent_node = await Node.create(name="1")
    child_node = await Node.create(name="2")
    tree = await Tree.create(parent=parent_node, child=child_node)
    tree = await Tree.all().select_related("parent", "child").get(pk=tree.pk)
    assert tree.parent.pk == parent_node.pk
    assert tree.parent.name == parent_node.name
    assert tree.child.pk == child_node.pk
    assert tree.child.name == child_node.name


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_postgres_search(db):
    name = "hello world"
    await Tournament.create(name=name)
    ret = await Tournament.filter(name__search="hello").first()
    assert ret.name == name


@pytest.mark.asyncio
async def test_subquery_select(db):
    t1 = await Tournament.create(name="1")
    ret = (
        await Tournament.filter(pk=t1.pk)
        .annotate(ids=Subquery(Tournament.filter(pk=t1.pk).values("id")))
        .values("ids", "id")
    )
    assert ret == [{"id": t1.pk, "ids": t1.pk}]


@pytest.mark.asyncio
async def test_subquery_filter(db):
    t1 = await Tournament.create(name="1")
    ret = await Tournament.filter(pk=Subquery(Tournament.filter(pk=t1.pk).values("id"))).first()
    assert ret == t1


@pytest.mark.asyncio
async def test_raw_sql_count(db):
    t1 = await Tournament.create(name="1")
    ret = await Tournament.filter(pk=t1.pk).annotate(count=RawSQL("count(*)")).values("count")
    assert ret == [{"count": 1}]


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_raw_sql_select(db):
    t1 = await Tournament.create(id=1, name="1")
    ret = (
        await Tournament.filter(pk=t1.pk).annotate(idp=RawSQL("id + 1")).filter(idp=2).values("idp")
    )
    assert ret == [{"idp": 2}]


@pytest.mark.asyncio
async def test_raw_sql_filter(db):
    ret = await Tournament.filter(pk=RawSQL("id + 1"))
    assert ret == []


@pytest.mark.asyncio
async def test_annotation_field_priorior_to_model_field(db):
    # Sometimes, field name in annotates also exist in model field sets
    # and may need lift the former's priority in select query construction.
    t1 = await Tournament.create(name="1")
    ret = await Tournament.filter(pk=t1.pk).annotate(id=RawSQL("id + 1")).values("id")
    assert ret == [{"id": t1.pk + 1}]


@pytest.mark.asyncio
async def test_f_annotation_referenced_in_annotation(db):
    instance = await IntFields.create(intnum=1)

    events = (
        await IntFields.filter(id=instance.id)
        .annotate(intnum_plus_1=F("intnum") + 1)
        .annotate(intnum_plus_2=F("intnum_plus_1") + 1)
    )
    assert len(events) == 1
    assert events[0].intnum_plus_1 == 2
    assert events[0].intnum_plus_2 == 3

    # in a single annotate call
    events = await IntFields.filter(id=instance.id).annotate(
        intnum_plus_1=F("intnum") + 1, intnum_plus_2=F("intnum_plus_1") + 1
    )
    assert len(events) == 1
    assert events[0].intnum_plus_1 == 2
    assert events[0].intnum_plus_2 == 3


@pytest.mark.asyncio
async def test_rawsql_annotation_referenced_in_annotation(db):
    instance = await IntFields.create(intnum=1)

    events = (
        await IntFields.filter(id=instance.id)
        .annotate(ten=RawSQL("20 / 2"))
        .annotate(ten_plus_1=F("ten") + 1)
    )

    assert len(events) == 1
    assert events[0].ten == 10
    assert events[0].ten_plus_1 == 11


@pytest.mark.asyncio
async def test_joins_in_arithmetic_expressions(db):
    author = await Author.create(name="1")
    await Book.create(name="1", author=author, rating=1)
    await Book.create(name="2", author=author, rating=5)

    ret = await Author.annotate(rating=Avg(F("books__rating") + 1))
    assert len(ret) == 1
    assert ret[0].rating == 4.0

    ret = await Author.annotate(rating=Avg(F("books__rating") * 2 - F("books__rating")))
    assert len(ret) == 1
    assert ret[0].rating == 3.0


@pytest.mark.asyncio
async def test_annotations_in_flat_values_list(db):
    author1 = await Author.create(name="1")
    author2 = await Author.create(name="2")
    author3 = await Author.create(name="3")
    await Book.create(name="1", author=author1, rating=1)
    await Book.create(name="2", author=author2, rating=3)
    await Book.create(name="3", author=author3, rating=5)

    subquery = Author.annotate(rating=Avg("books__rating")).filter(rating__gte=3)

    subquery_ret = await subquery.order_by("id").values_list("id", flat=True)
    assert len(subquery_ret) == 2
    assert subquery_ret[0] == author2.pk
    assert subquery_ret[1] == author3.pk

    ret = await Author.filter(id__in=Subquery(subquery.values_list("id", flat=True))).order_by("id")
    assert ret[0] == author2
    assert ret[1] == author3


# Tests for exception classes (no database needed, pure Python tests)
def test_does_not_exist():
    exp_cls: type[NotExistOrMultiple] = DoesNotExist
    assert str(exp_cls("old format")) == "old format"
    assert str(exp_cls(Tournament)) == exp_cls.TEMPLATE.format(Tournament.__name__)


def test_multiple_objects_returned():
    exp_cls: type[NotExistOrMultiple] = MultipleObjectsReturned
    assert str(exp_cls("old format")) == "old format"
    assert str(exp_cls(Tournament)) == exp_cls.TEMPLATE.format(Tournament.__name__)


@pytest.mark.asyncio
async def test_union_basic(db):
    t1 = await Tournament.create(name="T1")
    t2 = await Tournament.create(name="T2")
    t3 = await Tournament.create(name="T3")
    await Tournament.create(name="T4")

    qs1 = Tournament.filter(name__in=["T1", "T2"])
    qs2 = Tournament.filter(name="T3")

    result = await qs1.union(qs2)
    assert set(result) == {t1, t2, t3}


@pytest.mark.asyncio
async def test_union_all(db):
    t1 = await Tournament.create(name="T1")
    await Tournament.create(name="T2")

    qs1 = Tournament.filter(name="T1")
    qs2 = Tournament.filter(name="T1")

    result = await qs1.union(qs2, all=True)
    assert list(result) == [t1, t1]


@pytest.mark.asyncio
async def test_union_mixed_models(db):
    r1 = await Reporter.create(name="R1")
    r2 = await Reporter.create(name="R2")
    await Reporter.create(name="R3")
    t1 = await Tournament.create(name="T1")
    await Tournament.create(name="T2")

    qs1 = Tournament.filter(name="T1").only("id", "name")
    qs2 = Reporter.filter(name__in=["R1", "R2"]).only("id", "name")

    result = await qs1.union(qs2)
    assert set(result) == {t1, r1, r2}


@pytest.mark.parametrize(
    "orderings,expected_instances",
    [
        ("name", ["t2", "t1", "r1"]),
        ("-name", ["r1", "t1", "t2"]),
    ],
)
@pytest.mark.asyncio
async def test_union_order_by(db, orderings, expected_instances):
    t1 = await Tournament.create(name="C")
    await Reporter.create(name="A")
    t2 = await Tournament.create(name="B")
    await Reporter.create(name="D")
    await Tournament.create(name="E")
    r1 = await Reporter.create(name="F")

    qs1 = Tournament.filter(id__in=[t1.id, t2.id]).only("id", "name")
    qs2 = Reporter.filter(id=r1.id).only("id", "name")

    result = await qs1.union(qs2).order_by(*orderings.split(","))

    instance_map = {"t1": t1, "t2": t2, "r1": r1}
    expected = [instance_map[k] for k in expected_instances]

    assert result == expected


@pytest.mark.asyncio
async def test_union_order_by_multiple_fields(db):
    t1 = await Tournament.create(name="C")
    t2 = await Tournament.create(name="B")
    r1 = await Reporter.create(name="C")
    await Tournament.create(name="Z")
    await Reporter.create(name="Z")

    qs1 = Tournament.filter(id__in=[t1.id, t2.id]).only("id", "name")
    qs2 = Reporter.filter(id=r1.id).only("id", "name")

    result = await qs1.union(qs2).order_by("name", "id")

    if r1.id == t1.id:
        return

    if r1.id > t1.id:
        expected = [t2, t1, r1]
    else:
        expected = [t2, r1, t1]

    assert result == expected


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_union_limit(db):
    r1 = await Reporter.create(name="B")
    t1 = await Tournament.create(name="A")
    await Reporter.create(name="D")
    await Tournament.create(name="C")

    qs1 = Tournament.all().only("id", "name")
    qs2 = Reporter.all().only("id", "name")

    result = await qs1.union(qs2).order_by("name").limit(2)
    assert list(result) == [t1, r1]


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_union_offset(db):
    await Tournament.create(name="T1")
    await Tournament.create(name="T2")
    t3 = await Tournament.create(name="T3")
    t4 = await Tournament.create(name="T4")

    qs1 = Tournament.filter(name__in=["T1", "T2"]).only("id", "name")
    qs2 = Tournament.filter(name__in=["T3", "T4"]).only("id", "name")

    result = await qs1.union(qs2).order_by("name").limit(4).offset(2)
    assert list(result) == [t3, t4]


@pytest.mark.asyncio
async def test_union_offset_negative_raises(db):
    qs1 = Tournament.all().only("id", "name")
    qs2 = Tournament.all().only("id", "name")

    with pytest.raises(ParamsError, match="Offset should be non-negative number"):
        await qs1.union(qs2).offset(-1)


@pytest.mark.asyncio
async def test_union_chained(db):
    t1 = await Tournament.create(name="T1")
    t2 = await Tournament.create(name="T2")
    await Tournament.create(name="T3")
    r1 = await Reporter.create(name="R1")
    await Reporter.create(name="R2")

    qs1 = Tournament.filter(name="T1").only("id", "name")
    qs2 = Tournament.filter(name="T2").only("id", "name")
    qs3 = Reporter.filter(name="R1").only("id", "name")

    result = await qs1.union(qs2).union(qs3)
    assert set(result) == {t1, t2, r1}


@pytest.mark.asyncio
async def test_union_count(db):
    await Tournament.create(name="T1")
    await Reporter.create(name="R1")
    await Tournament.create(name="T2")
    await Reporter.create(name="R2")

    qs1 = Tournament.filter(name="T1").only("id")
    qs2 = Reporter.filter(name="R1").only("id")

    assert await qs1.union(qs2).count() == 2


@pytest.mark.asyncio
async def test_union_different_select_fields_raises(db):
    await Tournament.create(name="T1")

    qs1 = Tournament.filter(name="T1").only("name")
    qs2 = Tournament.filter(name="T1").only("desc")

    with pytest.raises(ParamsError, match="Union queries must have the same select fields"):
        await qs1.union(qs2)


@pytest.mark.asyncio
async def test_union_different_fields__in_different_models_raises(db):
    await Tournament.create(name="T1")
    await Reporter.create(name="R1")

    qs1 = Tournament.all()
    qs2 = Reporter.all()

    with pytest.raises(ParamsError, match="Union queries must have the same select fields"):
        await qs1.union(qs2)


@pytest.mark.asyncio
async def test_union_order_by_field_not_in_select_raises(db):
    await Tournament.create(name="T1")

    qs1 = Tournament.filter(name="T1").only("id", "name")
    qs2 = Tournament.filter(name="T1").only("id", "name")

    qs = qs1.union(qs2)
    with pytest.raises(ParamsError, match="Order by field must be in the select list"):
        await qs.order_by("desc")


@pytest.mark.asyncio
async def test_union_with_annotate_raises(db):
    await Tournament.create(name="T1")
    await Reporter.create(name="R1")

    qs1 = (
        Tournament.filter(name="T1")
        .annotate(annotated_value=Value(1))
        .only("id", "name", "annotated_value")
    )
    qs2 = (
        Reporter.filter(name="R1")
        .annotate(annotated_value=Value(1))
        .only("id", "name", "annotated_value")
    )

    with pytest.raises(ParamsError, match="Union queries do not support annotations"):
        await qs1.union(qs2)
