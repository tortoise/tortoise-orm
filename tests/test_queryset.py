from tests.testmodels import Event, IntFields, MinRelation, Node, Reporter, Tournament, Tree
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import (
    DoesNotExist,
    FieldError,
    IntegrityError,
    MultipleObjectsReturned,
    ParamsError,
)
from tortoise.expressions import F, Subquery

# TODO: Test the many exceptions in QuerySet
# TODO: .filter(intnum_null=None) does not work as expected


class TestQueryset(test.TestCase):
    async def setUp(self):
        # Build large dataset
        self.intfields = [await IntFields.create(intnum=val) for val in range(10, 100, 3)]
        self.db = Tortoise.get_connection("models")

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

    async def test_offset_count(self):
        self.assertEqual(await IntFields.all().offset(10).count(), 20)

    async def test_offset_negative(self):
        with self.assertRaisesRegex(ParamsError, "Offset should be non-negative number"):
            await IntFields.all().offset(-10)

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

    async def test_first(self):
        # Test first
        self.assertEqual(
            (await IntFields.all().order_by("intnum").filter(intnum__gte=40).first()).intnum, 40
        )

        self.assertEqual(
            await IntFields.all().order_by("intnum").filter(intnum__gte=400).first(), None
        )

    async def test_get_or_none(self):
        self.assertEqual((await IntFields.all().get_or_none(intnum=40)).intnum, 40)

        self.assertEqual(
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=400), None
        )

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().order_by("intnum").get_or_none(intnum__gte=40)

    async def test_get(self):
        await IntFields.filter(intnum__gte=70).update(intnum_null=80)

        # Test get
        self.assertEqual((await IntFields.all().get(intnum=40)).intnum, 40)

        self.assertEqual((await IntFields.all().all().all().all().all().get(intnum=40)).intnum, 40)

        self.assertEqual((await IntFields.get(intnum=40)).intnum, 40)

        with self.assertRaises(DoesNotExist):
            await IntFields.all().get(intnum=41)

        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=41)

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().get(intnum_null=80)

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.get(intnum_null=80)

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
        )[0]
        self.assertEqual(data[0] + 1, data[1])

    async def test_get_raw_sql(self):
        sql = IntFields.all().sql()
        self.assertRegex(sql, r"^SELECT.+FROM.+")

    @test.requireCapability(support_index_hint=True)
    async def test_force_index(self):
        sql = IntFields.filter(pk=1).only("id").force_index("index_name").sql()
        self.assertEqual(
            sql,
            "SELECT `id` `id` FROM `intfields` FORCE INDEX (`index_name`) WHERE `id`=1",
        )

    @test.requireCapability(support_index_hint=True)
    async def test_use_index(self):
        sql = IntFields.filter(pk=1).only("id").use_index("index_name").sql()
        self.assertEqual(
            sql,
            "SELECT `id` `id` FROM `intfields` USE INDEX (`index_name`) WHERE `id`=1",
        )

    @test.requireCapability(support_for_update=True)
    async def test_select_for_update(self):
        sql1 = IntFields.filter(pk=1).only("id").select_for_update().sql()
        sql2 = IntFields.filter(pk=1).only("id").select_for_update(nowait=True).sql()
        sql3 = IntFields.filter(pk=1).only("id").select_for_update(skip_locked=True).sql()
        sql4 = IntFields.filter(pk=1).only("id").select_for_update(of=("intfields",)).sql()

        dialect = self.db.schema_generator.DIALECT
        if dialect == "postgres":
            self.assertEqual(
                sql1,
                'SELECT "id" "id" FROM "intfields" WHERE "id"=1 FOR UPDATE',
            )
            self.assertEqual(
                sql2,
                'SELECT "id" "id" FROM "intfields" WHERE "id"=1 FOR UPDATE NOWAIT',
            )
            self.assertEqual(
                sql3,
                'SELECT "id" "id" FROM "intfields" WHERE "id"=1 FOR UPDATE SKIP LOCKED',
            )
            self.assertEqual(
                sql4,
                'SELECT "id" "id" FROM "intfields" WHERE "id"=1 FOR UPDATE OF "intfields"',
            )
        elif dialect == "mysql":
            self.assertEqual(
                sql1,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=1 FOR UPDATE",
            )
            self.assertEqual(
                sql2,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=1 FOR UPDATE NOWAIT",
            )
            self.assertEqual(
                sql3,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=1 FOR UPDATE SKIP LOCKED",
            )
            self.assertEqual(
                sql4,
                "SELECT `id` `id` FROM `intfields` WHERE `id`=1 FOR UPDATE OF `intfields`",
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
