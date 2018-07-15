from tortoise.contrib import test
from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned
from tortoise.tests.testmodels import IntFields

# TODO: Test the many exceptions in QuerySet
# TODO: Test limit/offset/ordering on values()
# TODO: Test distinct


class TestQueryset(test.TestCase):
    async def test_all_count(self):
        # Build large dataset
        for val in range(10, 100, 3):
            await IntFields.create(intnum=val)

        self.assertEqual(await IntFields.all().count(), 30)

        self.assertEqual(await IntFields.filter(intnum_null=80).count(), 0)

        # Modify dataset
        await IntFields.filter(intnum__gte=70).update(intnum_null=80)

        self.assertEqual(await IntFields.filter(intnum_null=80).count(), 10)

        # Test limit/offset/ordering
        self.assertEqual(
            await IntFields.all().order_by('intnum').limit(10).values_list('intnum', flat=True),
            [10, 13, 16, 19, 22, 25, 28, 31, 34, 37]
        )

        self.assertEqual(
            await IntFields.all().order_by('intnum').limit(10).offset(10).values_list(
                'intnum', flat=True),
            [40, 43, 46, 49, 52, 55, 58, 61, 64, 67]
        )

        self.assertEqual(
            await IntFields.all().order_by('intnum').limit(10).offset(20).values_list(
                'intnum', flat=True),
            [70, 73, 76, 79, 82, 85, 88, 91, 94, 97]
        )

        self.assertEqual(
            await IntFields.all().order_by('intnum').limit(10).offset(30).values_list(
                'intnum', flat=True),
            []
        )

        self.assertEqual(
            await IntFields.all().order_by('-intnum').limit(10).values_list('intnum', flat=True),
            [97, 94, 91, 88, 85, 82, 79, 76, 73, 70]
        )

        self.assertEqual(
            await IntFields.all().order_by('intnum').limit(10).filter(intnum__gte=40).values_list(
                'intnum', flat=True),
            [40, 43, 46, 49, 52, 55, 58, 61, 64, 67]
        )

        self.assertEqual(
            (await IntFields.all().order_by('intnum').filter(intnum__gte=40).first()).intnum,
            40
        )

        # Test get
        self.assertEqual(
            (await IntFields.all().get(intnum=40)).intnum,
            40
        )

        self.assertEqual(
            (await IntFields.all().all().all().all().all().get(intnum=40)).intnum,
            40
        )

        self.assertEqual(
            (await IntFields.get(intnum=40)).intnum,
            40
        )

        with self.assertRaises(DoesNotExist):
            await IntFields.all().get(intnum=41)

        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=41)

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.all().get(intnum_null=80)

        with self.assertRaises(MultipleObjectsReturned):
            await IntFields.get(intnum_null=80)

        # Test delete
        await (await IntFields.get(intnum=40)).delete()

        with self.assertRaises(DoesNotExist):
            await IntFields.get(intnum=40)

        self.assertEqual(await IntFields.all().count(), 29)

        await IntFields.all().order_by('intnum').limit(10).filter(intnum__gte=70).delete()

        self.assertEqual(await IntFields.all().count(), 19)

        # TODO: Should DELETE honour limit and offset?
        # await IntFields.all().order_by('intnum').limit(10).delete()
        #
        # self.assertEqual(
        #     await IntFields.all().order_by('intnum').values_list('intnum', flat=True),
        #     [10, 13, 16, 19, 22, 25, 28, 31, 34, 37]
        # )
