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
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
from tortoise.exceptions import (
    DoesNotExist,
    FieldError,
    IntegrityError,
    MultipleObjectsReturned,
    NotExistOrMultiple,
    ParamsError,
)
from tortoise.expressions import F, RawSQL, Subquery
from tortoise.functions import Avg

# TODO: Test the many exceptions in QuerySet
# TODO: .filter(intnum_null=None) does not work as expected


class TestQueryset(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        # Build large dataset
        self.intfields = [await IntFields.create(intnum=val) for val in range(10, 100, 3)]
        self.db = connections.get("models")

    async def test_all_count(self):
        self.assertEqual(await IntFields.all().count(), 30)
        self.assertEqual(await IntFields.filter(intnum_null=80).count(), 0)

    async def test_exists(self):
        ret = await IntFields.filter(intnum=0).exists()
        self.assertFalse(ret)

        ret = await IntFields.filter(intnum=10).exists()
        self.assertTrue(ret)

        ret = await IntFields.filter(intnum__gt=10).exists()
        self.assertTrue(ret)

        ret = await IntFields.filter(intnum__lt=10).exists()
        self.assertFalse(ret)

    async def test_limit_count(self):
        self.assertEqual(await IntFields.all().limit(10).count(), 10)

    async def test_limit_negative(self):
        with self.assertRaisesRegex(ParamsError, "Limit should be non-negative number"):
            await IntFields.all().limit(-10)

    @test.requireCapability(dialect="sqlite")
    async def test_limit_zero(self):
        sql = IntFields.all().only("id").limit(0).sql()
        self.assertEqual(
            sql,
            'SELECT "id" "id" FROM "intfields" LIMIT ?',
        )

    async def test_offset_count(self):
        self.assertEqual(await IntFields.all().offset(10).count(), 20)

    async def test_offset_negative(self):
        with self.assertRaisesRegex(ParamsError, "Offset should be non-negative number"):
            await IntFields.all().offset(-10)

    async def test_slicing_start_and_stop(self) -> None:
        sliced_queryset = IntFields.all().order_by("intnum")[1:5]
        manually_sliced_queryset = IntFields.all().order_by("intnum").offset(1).limit(4)
        self.assertSequenceEqual(await sliced_queryset, await manually_sliced_queryset)

    async def test_slicing_only_limit(self) -> None:
        sliced_queryset = IntFields.all().order_by("intnum")[:5]
        manually_sliced_queryset = IntFields.all().order_by("intnum").limit(5)
        self.assertSequenceEqual(await sliced_queryset, await manually_sliced_queryset)

    async def test_slicing_only_offset(self) -> None:
        sliced_queryset = IntFields.all().order_by("intnum")[5:]
        manually_sliced_queryset = IntFields.all().order_by("intnum").offset(5)
        self.assertSequenceEqual(await sliced_queryset, await manually_sliced_queryset)

    async def test_slicing_count(self) -> None:
        queryset = IntFields.all().order_by("intnum")[1:5]
        self.assertEqual(await queryset.count(), 4)

    def test_slicing_negative_values(self) -> None:
        with self.assertRaisesRegex(
            expected_exception=ParamsError,
            expected_regex="Slice start should be non-negative number or None.",
        ):
            _ = IntFields.all()[-1:]

        with self.assertRaisesRegex(
            expected_exception=ParamsError,
            expected_regex="Slice stop should be non-negative number greater that slice start, "
            "or None.",
        ):
            _ = IntFields.all()[:-1]

    def test_slicing_stop_before_start(self) -> None:
        with self.assertRaisesRegex(
            expected_exception=ParamsError,
            expected_regex="Slice stop should be non-negative number greater that slice start, "
            "or None.",
        ):
            _ = IntFields.all()[2:1]

    async def test_slicing_steps(self) -> None:
        sliced_queryset = IntFields.all().order_by("intnum")[::1]
        manually_sliced_queryset = IntFields.all().order_by("intnum")
        self.assertSequenceEqual(await sliced_queryset, await manually_sliced_queryset)

        with self.assertRaisesRegex(
            expected_exception=ParamsError,
            expected_regex="Slice steps should be 1 or None.",
        ):
            _ = IntFields.all()[::2]

    async def test_join_count(self):
        tour = await Tournament.create(name="moo")
        await MinRelation.create(tournament=tour)

        self.assertEqual(await MinRelation.all().count(), 1)
        self.assertEqual(await MinRelation.filter(tournament__id=tour.id).count(), 1)

    async def test_modify_dataset(self):
        # Modify dataset
        rows_affected = await IntFields.filter(intnum__gte=70).update(intnum_null=80)
        self.assertEqual(rows_affected, 10)
        self.assertEqual(await IntFields.filter(intnum_null=80).count(), 10)
        self.assertEqual(await IntFields.filter(intnum_null__isnull=True).count(), 20)
        await IntFields.filter(intnum_null__isnull=True).update(intnum_null=-1)
        self.assertEqual(await IntFields.filter(intnum_null=None).count(), 0)
        self.assertEqual(await IntFields.filter(intnum_null=-1).count(), 20)

    async def test_distinct(self):
        # Test distinct
        await IntFields.filter(intnum__gte=70).update(intnum_null=80)
        await IntFields.filter(intnum_null__isnull=True).update(intnum_null=-1)

        self.assertEqual(
            await IntFields.all()
            .order_by("intnum_null")
            .distinct()
            .values_list("intnum_null", flat=True),
            [-1, 80],
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum_null").distinct().values("intnum_null"),
            [{"intnum_null": -1}, {"intnum_null": 80}],
        )

    async def test_limit_offset_values_list(self):
        # Test limit/offset/ordering values_list
        self.assertEqual(
            await IntFields.all().order_by("intnum").limit(10).values_list("intnum", flat=True),
            [10, 13, 16, 19, 22, 25, 28, 31, 34, 37],
        )

        self.assertEqual(
            await IntFields.all()
            .order_by("intnum")
            .limit(10)
            .offset(10)
            .values_list("intnum", flat=True),
            [40, 43, 46, 49, 52, 55, 58, 61, 64, 67],
        )

        self.assertEqual(
            await IntFields.all()
            .order_by("intnum")
            .limit(10)
            .offset(20)
            .values_list("intnum", flat=True),
            [70, 73, 76, 79, 82, 85, 88, 91, 94, 97],
        )

        self.assertEqual(
            await IntFields.all()
            .order_by("intnum")
            .limit(10)
            .offset(30)
            .values_list("intnum", flat=True),
            [],
        )

        self.assertEqual(
            await IntFields.all().order_by("-intnum").limit(10).values_list("intnum", flat=True),
            [97, 94, 91, 88, 85, 82, 79, 76, 73, 70],
        )

        self.assertEqual(
            await IntFields.all()
            .order_by("intnum")
            .limit(10)
            .filter(intnum__gte=40)
            .values_list("intnum", flat=True),
            [40, 43, 46, 49, 52, 55, 58, 61, 64, 67],
        )

    async def test_limit_offset_values(self):
        # Test limit/offset/ordering values
        self.assertEqual(
            await IntFields.all().order_by("intnum").limit(5).values("intnum"),
            [{"intnum": 10}, {"intnum": 13}, {"intnum": 16}, {"intnum": 19}, {"intnum": 22}],
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum").limit(5).offset(10).values("intnum"),
            [{"intnum": 40}, {"intnum": 43}, {"intnum": 46}, {"intnum": 49}, {"intnum": 52}],
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum").limit(5).offset(30).values("intnum"), []
        )

        self.assertEqual(
            await IntFields.all().order_by("-intnum").limit(5).values("intnum"),
            [{"intnum": 97}, {"intnum": 94}, {"intnum": 91}, {"intnum": 88}, {"intnum": 85}],
        )

        self.assertEqual(
            await IntFields.all()
            .order_by("intnum")
            .limit(5)
            .filter(intnum__gte=40)
            .values("intnum"),
            [{"intnum": 40}, {"intnum": 43}, {"intnum": 46}, {"intnum": 49}, {"intnum": 52}],
        )

    async def test_in_bulk(self):
        id_list = [item.pk for item in await IntFields.all().only("id").limit(2)]
        ret = await IntFields.in_bulk(id_list=id_list)
        self.assertEqual(list(ret.keys()), id_list)

    async def test_first(self):
        # Test first
        self.assertEqual(
            (await IntFields.all().order_by("intnum").filter(intnum__gte=40).first()).intnum, 40
        )
        self.assertEqual(
            (await IntFields.all().order_by("intnum").filter(intnum__gte=40).first().values())[
                "intnum"
            ],
            40,
        )
        self.assertEqual(
            (await IntFields.all().order_by("intnum").filter(intnum__gte=40).first().values_list())[
                1
            ],
            40,
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum").filter(intnum__gte=400).first(), None
        )
        self.assertEqual(
            await IntFields.all().order_by("intnum").filter(intnum__gte=400).first().values(), None
        )
        self.assertEqual(
            await IntFields.all().order_by("intnum").filter(intnum__gte=400).first().values_list(),
            None,
        )

    async def test_last(self):
        self.assertEqual(
            (await IntFields.all().order_by("intnum").filter(intnum__gte=40).last()).intnum, 97
        )
        self.assertEqual(
            (await IntFields.all().order_by("intnum").filter(intnum__gte=40).last().values())[
                "intnum"
            ],
            97,
        )
        self.assertEqual(
            (await IntFields.all().order_by("intnum").filter(intnum__gte=40).last().values_list())[
                1
            ],
            97,
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum").filter(intnum__gte=400).last(), None
        )
        self.assertEqual(
            await IntFields.all().order_by("intnum").filter(intnum__gte=400).last().values(), None
        )
        self.assertEqual(
            await IntFields.all().order_by("intnum").filter(intnum__gte=400).last().values_list(),
            None,
        )
        self.assertEqual((await IntFields.all().filter(intnum__gte=40).last()).intnum, 97)

    async def test_latest(self):
        self.assertEqual((await IntFields.all().latest("intnum")).intnum, 97)
        self.assertEqual(
            (await IntFields.all().order_by("-intnum").first()).intnum,
            (await IntFields.all().latest("intnum")).intnum,
        )
        self.assertEqual((await IntFields.all().filter(intnum__gte=40).latest("intnum")).intnum, 97)
        self.assertEqual(
            (await IntFields.all().filter(intnum__gte=40).latest("intnum").values())["intnum"],
            97,
        )
        self.assertEqual(
            (await IntFields.all().filter(intnum__gte=40).latest("intnum").values_list())[1],
            97,
        )

        self.assertEqual(await IntFields.all().filter(intnum__gte=400).latest("intnum"), None)
        self.assertEqual(
            await IntFields.all().filter(intnum__gte=400).latest("intnum").values(), None
        )
        self.assertEqual(
            await IntFields.all().filter(intnum__gte=400).latest("intnum").values_list(),
            None,
        )

        with self.assertRaises(FieldError):
            await IntFields.all().latest()

        with self.assertRaises(FieldError):
            await IntFields.all().latest("some_unkown_field")

    async def test_earliest(self):
        self.assertEqual((await IntFields.all().earliest("intnum")).intnum, 10)
        self.assertEqual(
            (await IntFields.all().order_by("intnum").first()).intnum,
            (await IntFields.all().earliest("intnum")).intnum,
        )
        self.assertEqual(
            (await IntFields.all().filter(intnum__gte=40).earliest("intnum")).intnum, 40
        )
        self.assertEqual(
            (await IntFields.all().filter(intnum__gte=40).earliest("intnum").values())["intnum"],
            40,
        )
        self.assertEqual(
            (await IntFields.all().filter(intnum__gte=40).earliest("intnum").values_list())[1],
            40,
        )

        self.assertEqual(await IntFields.all().filter(intnum__gte=400).earliest("intnum"), None)
        self.assertEqual(
            await IntFields.all().filter(intnum__gte=400).earliest("intnum").values(), None
        )
        self.assertEqual(
            await IntFields.all().filter(intnum__gte=400).earliest("intnum").values_list(),
            None,
        )

        with self.assertRaises(FieldError):
            await IntFields.all().earliest()

        with self.assertRaises(FieldError):
            await IntFields.all().earliest("some_unkown_field")

    async def test_get_or_none(self):
        self.assertEqual((await IntFields.all().get_or_none(intnum=40)).intnum, 40)
        self.assertEqual((await IntFields.all().get_or_none(intnum=40).values())["intnum"], 40)
        self.assertEqual((await IntFields.all().get_or_none(intnum=40).values_list())[1], 40)

        self.assertEqual(
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=400), None
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=400).values(), None
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=400).values_list(),
            None,
        )

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=40)

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=40).values()

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=40).values_list()

    async def test_get(self):
        await IntFields.filter(intnum__gte=70).update(intnum_null=80)

        # Test get
        self.assertEqual((await IntFields.all().get(intnum=40)).intnum, 40)
        self.assertEqual((await IntFields.all().get(intnum=40).values())["intnum"], 40)
        self.assertEqual((await IntFields.all().get(intnum=40).values_list())[1], 40)

        self.assertEqual((await IntFields.all().all().all().all().all().get(intnum=40)).intnum, 40)
        self.assertEqual(
            (await IntFields.all().all().all().all().all().get(intnum=40).values())["intnum"], 40
        )
        self.assertEqual(
            (await IntFields.all().all().all().all().all().get(intnum=40).values_list())[1], 40
        )

        self.assertEqual((await IntFields.get(intnum=40)).intnum, 40)
        self.assertEqual((await IntFields.get(intnum=40).values())["intnum"], 40)
        self.assertEqual((await IntFields.get(intnum=40).values_list())[1], 40)

        with self.assertRaises(DoesNotExist):
            await IntFields.all().get(intnum=41)

        with self.assertRaises(DoesNotExist):
            await IntFields.all().get(intnum=41).values()

        with self.assertRaises(DoesNotExist):
            await IntFields.all().get(intnum=41).values_list()

        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=41)

        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=41).values()

        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=41).values_list()

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().get(intnum_null=80)

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().get(intnum_null=80).values()

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().get(intnum_null=80).values_list()

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.get(intnum_null=80)

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.get(intnum_null=80).values()

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.get(intnum_null=80).values_list()

    async def test_delete(self):
        # Test delete
        await (await IntFields.get(intnum=40)).delete()

        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=40)

        self.assertEqual(await IntFields.all().count(), 29)

        rows_affected = (
            await IntFields.all().order_by("intnum").limit(10).filter(intnum__gte=70).delete()
        )
        self.assertEqual(rows_affected, 10)

        self.assertEqual(await IntFields.all().count(), 19)

    @test.requireCapability(support_update_limit_order_by=True)
    async def test_delete_limit(self):
        await IntFields.all().limit(1).delete()
        self.assertEqual(await IntFields.all().count(), 29)

    @test.requireCapability(support_update_limit_order_by=True)
    async def test_delete_limit_order_by(self):
        await IntFields.all().limit(1).order_by("-id").delete()
        self.assertEqual(await IntFields.all().count(), 29)
        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=97)

    async def test_async_iter(self):
        counter = 0
        async for _ in IntFields.all():
            counter += 1

        self.assertEqual(await IntFields.all().count(), counter)

    async def test_update_basic(self):
        obj0 = await IntFields.create(intnum=2147483647)
        await IntFields.filter(id=obj0.id).update(intnum=2147483646)
        obj = await IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 2147483646)
        self.assertEqual(obj.intnum_null, None)

    async def test_update_f_expression(self):
        obj0 = await IntFields.create(intnum=2147483647)
        await IntFields.filter(id=obj0.id).update(intnum=F("intnum") - 1)
        obj = await IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 2147483646)

    async def test_update_badparam(self):
        obj0 = await IntFields.create(intnum=2147483647)
        with self.assertRaisesRegex(FieldError, "Unknown keyword argument"):
            await IntFields.filter(id=obj0.id).update(badparam=1)

    async def test_update_pk(self):
        obj0 = await IntFields.create(intnum=2147483647)
        with self.assertRaisesRegex(IntegrityError, "is PK and can not be updated"):
            await IntFields.filter(id=obj0.id).update(id=1)

    async def test_update_virtual(self):
        tour = await Tournament.create(name="moo")
        obj0 = await MinRelation.create(tournament=tour)
        with self.assertRaisesRegex(FieldError, "is virtual and can not be updated"):
            await MinRelation.filter(id=obj0.id).update(participants=[])

    async def test_bad_ordering(self):
        with self.assertRaisesRegex(FieldError, "Unknown field moo1fip for model IntFields"):
            await IntFields.all().order_by("moo1fip")

    async def test_duplicate_values(self):
        with self.assertRaisesRegex(FieldError, "Duplicate key intnum"):
            await IntFields.all().values("intnum", "intnum")

    async def test_duplicate_values_list(self):
        await IntFields.all().values_list("intnum", "intnum")

    async def test_duplicate_values_kw(self):
        with self.assertRaisesRegex(FieldError, "Duplicate key intnum"):
            await IntFields.all().values("intnum", intnum="intnum_null")

    async def test_duplicate_values_kw_badmap(self):
        with self.assertRaisesRegex(FieldError, 'Unknown field "intnum2" for model "IntFields"'):
            await IntFields.all().values(intnum="intnum2")

    async def test_bad_values(self):
        with self.assertRaisesRegex(FieldError, 'Unknown field "int2num" for model "IntFields"'):
            await IntFields.all().values("int2num")

    async def test_bad_values_list(self):
        with self.assertRaisesRegex(FieldError, 'Unknown field "int2num" for model "IntFields"'):
            await IntFields.all().values_list("int2num")

    async def test_many_flat_values_list(self):
        with self.assertRaisesRegex(
            TypeError, "You can flat value_list only if contains one field"
        ):
            await IntFields.all().values_list("intnum", "intnum_null", flat=True)

    async def test_all_flat_values_list(self):
        with self.assertRaisesRegex(
            TypeError, "You can flat value_list only if contains one field"
        ):
            await IntFields.all().values_list(flat=True)

    async def test_all_values_list(self):
        data = await IntFields.all().order_by("id").values_list()
        self.assertEqual(data[2], (self.intfields[2].id, 16, None))

    async def test_all_values(self):
        data = await IntFields.all().order_by("id").values()
        self.assertEqual(data[2], {"id": self.intfields[2].id, "intnum": 16, "intnum_null": None})

    async def test_order_by_bad_value(self):
        with self.assertRaisesRegex(FieldError, "Unknown field badid for model IntFields"):
            await IntFields.all().order_by("badid").values_list()

    async def test_annotate_order_expression(self):
        data = (
            await IntFields.annotate(idp=F("id") + 1)
            .order_by("-idp")
            .first()
            .values_list("id", "idp")
        )
        self.assertEqual(data[0] + 1, data[1])

    async def test_annotate_order_rawsql(self):
        qs = IntFields.annotate(idp=RawSQL("id+1")).order_by("-idp")
        data = await qs.first().values_list("id", "idp")
        self.assertEqual(data[0] + 1, data[1])

    async def test_annotate_expression_filter(self):
        count = await IntFields.annotate(intnum1=F("intnum") + 1).filter(intnum1__gt=30).count()
        self.assertEqual(count, 23)

    async def test_get_raw_sql(self):
        sql = IntFields.all().sql()
        self.assertRegex(sql, r"^SELECT.+FROM.+")

    @test.requireCapability(support_index_hint=True)
    async def test_force_index(self):
        sql = IntFields.filter(pk=1).only("id").force_index("index_name").sql()
        self.assertEqual(
            sql,
            "SELECT `id` `id` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_again = IntFields.filter(pk=1).only("id").force_index("index_name").sql()
        self.assertEqual(
            sql_again,
            "SELECT `id` `id` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s",
        )

    @test.requireCapability(support_index_hint=True)
    async def test_force_index_available_in_more_query(self):
        sql_ValuesQuery = IntFields.filter(pk=1).force_index("index_name").values("id").sql()
        self.assertEqual(
            sql_ValuesQuery,
            "SELECT `id` `id` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_ValuesListQuery = (
            IntFields.filter(pk=1).force_index("index_name").values_list("id").sql()
        )
        self.assertEqual(
            sql_ValuesListQuery,
            "SELECT `id` `0` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_CountQuery = IntFields.filter(pk=1).force_index("index_name").count().sql()
        self.assertEqual(
            sql_CountQuery,
            "SELECT COUNT(*) FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_ExistsQuery = IntFields.filter(pk=1).force_index("index_name").exists().sql()
        self.assertEqual(
            sql_ExistsQuery,
            "SELECT 1 FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=%s LIMIT %s",
        )

    @test.requireCapability(support_index_hint=True)
    async def test_use_index(self):
        sql = IntFields.filter(pk=1).only("id").use_index("index_name").sql()
        self.assertEqual(
            sql,
            "SELECT `id` `id` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_again = IntFields.filter(pk=1).only("id").use_index("index_name").sql()
        self.assertEqual(
            sql_again,
            "SELECT `id` `id` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s",
        )

    @test.requireCapability(support_index_hint=True)
    async def test_use_index_available_in_more_query(self):
        sql_ValuesQuery = IntFields.filter(pk=1).use_index("index_name").values("id").sql()
        self.assertEqual(
            sql_ValuesQuery,
            "SELECT `id` `id` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_ValuesListQuery = IntFields.filter(pk=1).use_index("index_name").values_list("id").sql()
        self.assertEqual(
            sql_ValuesListQuery,
            "SELECT `id` `0` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_CountQuery = IntFields.filter(pk=1).use_index("index_name").count().sql()
        self.assertEqual(
            sql_CountQuery,
            "SELECT COUNT(*) FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s",
        )

        sql_ExistsQuery = IntFields.filter(pk=1).use_index("index_name").exists().sql()
        self.assertEqual(
            sql_ExistsQuery,
            "SELECT 1 FROM `intfields` USE INDEX (`index_name`) WHERE `id`=%s LIMIT %s",
        )

    @test.requireCapability(support_for_update=True)
    async def test_select_for_update(self):
        sql1 = IntFields.filter(pk=1).only("id").select_for_update().sql()
        sql2 = IntFields.filter(pk=1).only("id").select_for_update(nowait=True).sql()
        sql3 = IntFields.filter(pk=1).only("id").select_for_update(skip_locked=True).sql()
        sql4 = IntFields.filter(pk=1).only("id").select_for_update(of=("intfields",)).sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "postgres":
            if isinstance(self.db, PsycopgClient):
                self.assertEqual(
                    sql1,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE',
                )
                self.assertEqual(
                    sql2,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE NOWAIT',
                )
                self.assertEqual(
                    sql3,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE SKIP LOCKED',
                )
                self.assertEqual(
                    sql4,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=%s FOR UPDATE OF "intfields"',
                )
            else:
                self.assertEqual(
                    sql1,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE',
                )
                self.assertEqual(
                    sql2,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE NOWAIT',
                )
                self.assertEqual(
                    sql3,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE SKIP LOCKED',
                )
                self.assertEqual(
                    sql4,
                    'SELECT "id" "id" FROM "intfields" WHERE "id"=$1 FOR UPDATE OF "intfields"',
                )
        elif dialect == "mysql":
            self.assertEqual(
                sql1,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE",
            )
            self.assertEqual(
                sql2,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE NOWAIT",
            )
            self.assertEqual(
                sql3,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE SKIP LOCKED",
            )
            self.assertEqual(
                sql4,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=%s FOR UPDATE OF `intfields`",
            )

    async def test_select_related(self):
        tournament = await Tournament.create(name="1")
        reporter = await Reporter.create(name="Reporter")
        event = await Event.create(name="1", tournament=tournament, reporter=reporter)
        event = await Event.all().select_related("tournament", "reporter").get(pk=event.pk)
        self.assertEqual(event.tournament.pk, tournament.pk)
        self.assertEqual(event.reporter.pk, reporter.pk)

    async def test_select_related_with_two_same_models(self):
        parent_node = await Node.create(name="1")
        child_node = await Node.create(name="2")
        tree = await Tree.create(parent=parent_node, child=child_node)
        tree = await Tree.all().select_related("parent", "child").get(pk=tree.pk)
        self.assertEqual(tree.parent.pk, parent_node.pk)
        self.assertEqual(tree.parent.name, parent_node.name)
        self.assertEqual(tree.child.pk, child_node.pk)
        self.assertEqual(tree.child.name, child_node.name)

    @test.requireCapability(dialect="postgres")
    async def test_postgres_search(self):
        name = "hello world"
        await Tournament.create(name=name)
        ret = await Tournament.filter(name__search="hello").first()
        self.assertEqual(ret.name, name)

    async def test_subquery_select(self):
        t1 = await Tournament.create(name="1")
        ret = (
            await Tournament.filter(pk=t1.pk)
            .annotate(ids=Subquery(Tournament.filter(pk=t1.pk).values("id")))
            .values("ids", "id")
        )
        self.assertEqual(ret, [{"id": t1.pk, "ids": t1.pk}])

    async def test_subquery_filter(self):
        t1 = await Tournament.create(name="1")
        ret = await Tournament.filter(pk=Subquery(Tournament.filter(pk=t1.pk).values("id"))).first()
        self.assertEqual(ret, t1)

    async def test_raw_sql_count(self):
        t1 = await Tournament.create(name="1")
        ret = await Tournament.filter(pk=t1.pk).annotate(count=RawSQL("count(*)")).values("count")
        self.assertEqual(ret, [{"count": 1}])

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_raw_sql_select(self):
        t1 = await Tournament.create(id=1, name="1")
        ret = (
            await Tournament.filter(pk=t1.pk)
            .annotate(idp=RawSQL("id + 1"))
            .filter(idp=2)
            .values("idp")
        )
        self.assertEqual(ret, [{"idp": 2}])

    async def test_raw_sql_filter(self):
        ret = await Tournament.filter(pk=RawSQL("id + 1"))
        self.assertEqual(ret, [])

    async def test_annotation_field_priorior_to_model_field(self):
        # Sometimes, field name in annotates also exist in model field sets
        # and may need lift the former's priority in select query construction.
        t1 = await Tournament.create(name="1")
        ret = await Tournament.filter(pk=t1.pk).annotate(id=RawSQL("id + 1")).values("id")
        self.assertEqual(ret, [{"id": t1.pk + 1}])

    async def test_f_annotation_referenced_in_annotation(self):
        instance = await IntFields.create(intnum=1)

        events = (
            await IntFields.filter(id=instance.id)
            .annotate(intnum_plus_1=F("intnum") + 1)
            .annotate(intnum_plus_2=F("intnum_plus_1") + 1)
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].intnum_plus_1, 2)
        self.assertEqual(events[0].intnum_plus_2, 3)

        # in a single annotate call
        events = await IntFields.filter(id=instance.id).annotate(
            intnum_plus_1=F("intnum") + 1, intnum_plus_2=F("intnum_plus_1") + 1
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].intnum_plus_1, 2)
        self.assertEqual(events[0].intnum_plus_2, 3)

    async def test_rawsql_annotation_referenced_in_annotation(self):
        instance = await IntFields.create(intnum=1)

        events = (
            await IntFields.filter(id=instance.id)
            .annotate(ten=RawSQL("20 / 2"))
            .annotate(ten_plus_1=F("ten") + 1)
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].ten, 10)
        self.assertEqual(events[0].ten_plus_1, 11)

    async def test_joins_in_arithmetic_expressions(self):
        author = await Author.create(name="1")
        await Book.create(name="1", author=author, rating=1)
        await Book.create(name="2", author=author, rating=5)

        ret = await Author.annotate(rating=Avg(F("books__rating") + 1))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].rating, 4.0)

        ret = await Author.annotate(rating=Avg(F("books__rating") * 2 - F("books__rating")))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].rating, 3.0)


class TestNotExist(test.TestCase):
    exp_cls: type[NotExistOrMultiple] = DoesNotExist

    @test.requireCapability(dialect="sqlite")
    def test_does_not_exist(self):
        assert str(self.exp_cls("old format")) == "old format"
        assert str(self.exp_cls(Tournament)) == self.exp_cls.TEMPLATE.format(Tournament.__name__)


class TestMultiple(TestNotExist):
    exp_cls = MultipleObjectsReturned
