from tortoise.contrib import test
from tortoise.exceptions import DoesNotExist
from tortoise.tests.testmodels import IntFields


class TestQueryset(test.TestCase):
    async def test_all_count(self):
        self.ints = [
            await IntFields.create(intnum=val)
            for val in range(10, 100, 3)
        ]

        self.assertEqual(await IntFields.all().count(), 30)

        self.assertEqual(await IntFields.filter(intnum_null=80).count(), 0)

        await IntFields.filter(intnum__gte=70).update(intnum_null=80)

        self.assertEqual(await IntFields.filter(intnum_null=80).count(), 10)

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

        self.assertEqual(
            (await IntFields.all().get(intnum=40)).intnum,
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

        # TODO: Must raise MultipleObjectsReturned
        # self.assertEqual(
        #     (await IntFields.all().get(intnum_null=80)).intnum,
        #     40
        # )
        #
        # self.assertEqual(
        #     (await IntFields.get(intnum_null=80)).intnum,
        #     40
        # )

        await IntFields.all().order_by('intnum').limit(10).filter(intnum__gte=70).delete()

        self.assertEqual(await IntFields.all().count(), 20)

        # TODO: Should DELETE honour limit and offset?
        # await IntFields.all().order_by('intnum').limit(10).delete()
        #
        # self.assertEqual(
        #     await IntFields.all().order_by('intnum').values_list('intnum', flat=True),
        #     [10, 13, 16, 19, 22, 25, 28, 31, 34, 37]
        # )
