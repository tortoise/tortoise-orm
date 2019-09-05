from tortoise.contrib import test
from tortoise.exceptions import DoesNotExist, FieldError, IntegrityError, MultipleObjectsReturned
from tortoise.tests.testmodels import IntFields, MinRelation, Tournament

# TODO: Test the many exceptions in QuerySet
# TODO: .filter(intnum_null=None) does not work as expected


class TestQueryset(test.TestCase):
    async def setUp(self):
        # Build large dataset
        for val in range(10, 100, 3):
            await IntFields.create(intnum=val)

    async def test_all_count(self):
        self.assertEqual(await IntFields.all().count(), 30)
        self.assertEqual(await IntFields.filter(intnum_null=80).count(), 0)

    async def test_join_count(self):
        tour = await Tournament.create(name="moo")
        await MinRelation.create(tournament=tour)

        self.assertEqual(await MinRelation.all().count(), 1)
        self.assertEqual(await MinRelation.filter(tournament__id=tour.id).count(), 1)

    async def test_modify_dataset(self):
        # Modify dataset
        await IntFields.filter(intnum__gte=70).update(intnum_null=80)
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

        await IntFields.all().order_by("intnum").limit(10).filter(intnum__gte=70).delete()

        self.assertEqual(await IntFields.all().count(), 19)

        # TODO: Should DELETE honour limit and offset?
        # await IntFields.all().order_by('intnum').limit(10).delete()
        #
        # self.assertEqual(
        #     await IntFields.all().order_by('intnum').values_list('intnum', flat=True),
        #     [10, 13, 16, 19, 22, 25, 28, 31, 34, 37]
        # )

    async def test_async_iter(self):
        counter = 0
        async for _ in IntFields.all():  # noqa
            counter += 1

        self.assertEqual(await IntFields.all().count(), counter)

    async def test_update_basic(self):
        obj0 = await IntFields.create(intnum=2147483647)
        await IntFields.filter(id=obj0.id).update(intnum=2147483646)
        obj = await IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 2147483646)
        self.assertEqual(obj.intnum_null, None)

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
