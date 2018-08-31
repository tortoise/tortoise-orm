from tortoise.contrib import test
from tortoise.tests.testmodels import CharFields


class TestFieldFilters(test.TestCase):
    async def setUp(self):
        await CharFields.create(char='moo')
        await CharFields.create(char='baa', char_null='baa')
        await CharFields.create(char='oink')

    async def test_equal(self):
        self.assertEqual(
            set(await CharFields.filter(char='moo').values_list('char', flat=True)),
            {'moo'}
        )

    async def test_not(self):
        self.assertEqual(
            set(await CharFields.filter(char__not='moo').values_list('char', flat=True)),
            {'baa', 'oink'}
        )

    async def test_in(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__in=['moo', 'baa']).values_list('char', flat=True)),
            {'moo', 'baa'}
        )

    async def test_not_in(self):
        self.assertSetEqual(
            set(await CharFields.filter(
                char__not_in=['moo', 'baa']).values_list('char', flat=True)),
            {'oink'}
        )

    async def test_isnull(self):
        self.assertSetEqual(
            set(await CharFields.filter(char_null__isnull=True).values_list('char', flat=True)),
            {'moo', 'oink'}
        )
        self.assertSetEqual(
            set(await CharFields.filter(char_null__isnull=False).values_list('char', flat=True)),
            {'baa'}
        )

    async def test_not_isnull(self):
        self.assertSetEqual(
            set(await CharFields.filter(char_null__not_isnull=True).values_list('char', flat=True)),
            {'baa'}
        )
        self.assertSetEqual(
            set(await CharFields.filter(
                char_null__not_isnull=False).values_list('char', flat=True)),
            {'moo', 'oink'}
        )

    async def test_gte(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__gte='moo').values_list('char', flat=True)),
            {'moo', 'oink'}
        )

    async def test_lte(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__lte='moo').values_list('char', flat=True)),
            {'moo', 'baa'}
        )

    async def test_gt(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__gt='moo').values_list('char', flat=True)),
            {'oink'}
        )

    async def test_lt(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__lt='moo').values_list('char', flat=True)),
            {'baa'}
        )

    async def test_contains(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__contains='o').values_list('char', flat=True)),
            {'moo', 'oink'}
        )

    async def test_startswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__startswith='m').values_list('char', flat=True)),
            {'moo'}
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__startswith='s').values_list('char', flat=True)),
            set()
        )

    async def test_endswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__endswith='o').values_list('char', flat=True)),
            {'moo'}
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__endswith='s').values_list('char', flat=True)),
            set()
        )

    async def test_icontains(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__icontains='oO').values_list('char', flat=True)),
            {'moo'}
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__icontains='Oo').values_list('char', flat=True)),
            {'moo'}
        )

    async def test_istartswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__istartswith='m').values_list('char', flat=True)),
            {'moo'}
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__istartswith='M').values_list('char', flat=True)),
            {'moo'}
        )

    async def test_iendswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__iendswith='oO').values_list('char', flat=True)),
            {'moo'}
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__iendswith='Oo').values_list('char', flat=True)),
            {'moo'}
        )
