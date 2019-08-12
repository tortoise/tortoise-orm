from tortoise.contrib import test
from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned, OperationalError
from tortoise.tests.testmodels import NoID, Tournament


class TestModelMethods(test.TestCase):
    async def setUp(self):
        self.mdl = await Tournament.create(name="Test")
        self.mdl2 = Tournament(name="Test")
        self.cls = Tournament

    async def test_save(self):
        oldid = self.mdl.id
        await self.mdl.save()
        self.assertEqual(self.mdl.id, oldid)

    async def test_save_full(self):
        self.mdl.name = "TestS"
        self.mdl.desc = "Something"
        await self.mdl.save()
        n_mdl = await self.cls.get(id=self.mdl.id)
        self.assertEqual(n_mdl.name, "TestS")
        self.assertEqual(n_mdl.desc, "Something")

    async def test_save_partial(self):
        self.mdl.name = "TestS"
        self.mdl.desc = "Something"
        await self.mdl.save(update_fields=["desc"])
        n_mdl = await self.cls.get(id=self.mdl.id)
        self.assertEqual(n_mdl.name, "Test")
        self.assertEqual(n_mdl.desc, "Something")

    async def test_create(self):
        mdl = self.cls(name="Test2")
        self.assertIsNone(mdl.id)
        await mdl.save()
        self.assertIsNotNone(mdl.id)

    async def test_delete(self):
        mdl = await self.cls.get(name="Test")
        self.assertEqual(self.mdl.id, mdl.id)

        await self.mdl.delete()

        with self.assertRaises(DoesNotExist):
            await self.cls.get(name="Test")

        with self.assertRaises(OperationalError):
            await self.mdl2.delete()

    def test_str(self):
        self.assertEqual(str(self.mdl), "Test")

    def test_repr(self):
        self.assertEqual(repr(self.mdl), "<Tournament: {}>".format(self.mdl.id))
        self.assertEqual(repr(self.mdl2), "<Tournament>")

    def test_hash(self):
        self.assertEqual(hash(self.mdl), self.mdl.id)
        with self.assertRaises(TypeError):
            hash(self.mdl2)

    async def test_eq(self):
        mdl = await self.cls.get(name="Test")
        self.assertEqual(self.mdl, mdl)

    async def test_get_or_create(self):
        mdl, created = await self.cls.get_or_create(name="Test")
        self.assertFalse(created)
        self.assertEqual(self.mdl, mdl)
        mdl, created = await self.cls.get_or_create(name="Test2")
        self.assertTrue(created)
        self.assertNotEqual(self.mdl, mdl)
        mdl2 = await self.cls.get(name="Test2")
        self.assertEqual(mdl, mdl2)

    async def test_first(self):
        mdl = await self.cls.first()
        self.assertEqual(self.mdl.id, mdl.id)

    async def test_filter(self):
        mdl = await self.cls.filter(name="Test").first()
        self.assertEqual(self.mdl.id, mdl.id)
        mdl = await self.cls.filter(name="Test2").first()
        self.assertIsNone(mdl)

    async def test_all(self):
        mdls = list(await self.cls.all())
        self.assertEqual(len(mdls), 1)
        self.assertEqual(mdls, [self.mdl])

    async def test_get(self):
        mdl = await self.cls.get(name="Test")
        self.assertEqual(self.mdl.id, mdl.id)

        with self.assertRaises(DoesNotExist):
            await self.cls.get(name="Test2")

        await self.cls.create(name="Test")

        with self.assertRaises(MultipleObjectsReturned):
            await self.cls.get(name="Test")


class TestModelMethodsNoID(TestModelMethods):
    async def setUp(self):
        self.mdl = await NoID.create(name="Test")
        self.mdl2 = NoID(name="Test")
        self.cls = NoID

    def test_str(self):
        self.assertEqual(str(self.mdl), "<NoID>")

    def test_repr(self):
        self.assertEqual(repr(self.mdl), "<NoID: {}>".format(self.mdl.id))
        self.assertEqual(repr(self.mdl2), "<NoID>")
