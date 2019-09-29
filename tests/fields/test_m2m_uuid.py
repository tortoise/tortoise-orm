from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import OperationalError


class TestManyToManyUUIDField(test.TestCase):
    UUIDPkModel = testmodels.UUIDPkModel
    UUIDM2MRelatedModel = testmodels.UUIDM2MRelatedModel

    async def test_empty(self):
        await self.UUIDM2MRelatedModel.create()

    async def test__add(self):
        one = await self.UUIDM2MRelatedModel.create()
        two = await self.UUIDPkModel.create()
        await one.models.add(two)
        self.assertEqual(await one.models, [two])
        self.assertEqual(await two.peers, [one])

    async def test__add__nothing(self):
        one = await self.UUIDPkModel.create()
        await one.peers.add()

    async def test__add__reverse(self):
        one = await self.UUIDM2MRelatedModel.create()
        two = await self.UUIDPkModel.create()
        await two.peers.add(one)
        self.assertEqual(await one.models, [two])
        self.assertEqual(await two.peers, [one])

    async def test__add__many(self):
        one = await self.UUIDPkModel.create()
        two = await self.UUIDM2MRelatedModel.create()
        await one.peers.add(two)
        await one.peers.add(two)
        await two.models.add(one)
        self.assertEqual(await one.peers, [two])
        self.assertEqual(await two.models, [one])

    async def test__add__two(self):
        one = await self.UUIDPkModel.create()
        two1 = await self.UUIDM2MRelatedModel.create()
        two2 = await self.UUIDM2MRelatedModel.create()
        await one.peers.add(two1, two2)
        self.assertEqual(set(await one.peers), {two1, two2})
        self.assertEqual(await two1.models, [one])
        self.assertEqual(await two2.models, [one])

    async def test__add__two_two(self):
        one1 = await self.UUIDPkModel.create()
        one2 = await self.UUIDPkModel.create()
        two1 = await self.UUIDM2MRelatedModel.create()
        two2 = await self.UUIDM2MRelatedModel.create()
        await one1.peers.add(two1, two2)
        await one2.peers.add(two1, two2)
        self.assertEqual(set(await one1.peers), {two1, two2})
        self.assertEqual(set(await one2.peers), {two1, two2})
        self.assertEqual(set(await two1.models), {one1, one2})
        self.assertEqual(set(await two2.models), {one1, one2})

    async def test__remove(self):
        one = await self.UUIDPkModel.create()
        two1 = await self.UUIDM2MRelatedModel.create()
        two2 = await self.UUIDM2MRelatedModel.create()
        await one.peers.add(two1, two2)
        await one.peers.remove(two1)
        self.assertEqual(await one.peers, [two2])
        self.assertEqual(await two1.models, [])
        self.assertEqual(await two2.models, [one])

    async def test__remove__many(self):
        one = await self.UUIDPkModel.create()
        two1 = await self.UUIDM2MRelatedModel.create()
        two2 = await self.UUIDM2MRelatedModel.create()
        two3 = await self.UUIDM2MRelatedModel.create()
        await one.peers.add(two1, two2, two3)
        await one.peers.remove(two1, two2)
        self.assertEqual(await one.peers, [two3])
        self.assertEqual(await two1.models, [])
        self.assertEqual(await two2.models, [])
        self.assertEqual(await two3.models, [one])

    async def test__remove__blank(self):
        one = await self.UUIDPkModel.create()
        with self.assertRaisesRegex(OperationalError, r"remove\(\) called on no instances"):
            await one.peers.remove()

    async def test__clear(self):
        one = await self.UUIDPkModel.create()
        two1 = await self.UUIDM2MRelatedModel.create()
        two2 = await self.UUIDM2MRelatedModel.create()
        await one.peers.add(two1, two2)
        await one.peers.clear()
        self.assertEqual(await one.peers, [])
        self.assertEqual(await two1.models, [])
        self.assertEqual(await two2.models, [])

    async def test__uninstantiated_add(self):
        one = self.UUIDPkModel()
        two = await self.UUIDM2MRelatedModel.create()
        with self.assertRaisesRegex(OperationalError, r"You should first call .save\(\) on"):
            await one.peers.add(two)

    async def test__add_uninstantiated(self):
        one = self.UUIDPkModel()
        two = await self.UUIDM2MRelatedModel.create()
        with self.assertRaisesRegex(OperationalError, r"You should first call .save\(\) on"):
            await two.models.add(one)

    # TODO: Sorting?


class TestManyToManyUUIDSourceField(TestManyToManyUUIDField):
    UUIDPkModel = testmodels.UUIDPkSourceModel  # type: ignore
    UUIDM2MRelatedModel = testmodels.UUIDM2MRelatedSourceModel  # type: ignore
