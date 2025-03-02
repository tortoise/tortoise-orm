from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import OperationalError
from tortoise.fields import ManyToManyField


class TestManyToManyField(test.TestCase):
    async def test_empty(self):
        await testmodels.M2MOne.create()

    async def test__add(self):
        one = await testmodels.M2MOne.create(name="One")
        two = await testmodels.M2MTwo.create(name="Two")
        await one.two.add(two)
        self.assertEqual(await one.two, [two])
        self.assertEqual(await two.one, [one])

    async def test__add__nothing(self):
        one = await testmodels.M2MOne.create(name="One")
        await one.two.add()

    async def test__add__reverse(self):
        one = await testmodels.M2MOne.create(name="One")
        two = await testmodels.M2MTwo.create(name="Two")
        await two.one.add(one)
        self.assertEqual(await one.two, [two])
        self.assertEqual(await two.one, [one])

    async def test__add__many(self):
        one = await testmodels.M2MOne.create(name="One")
        two = await testmodels.M2MTwo.create(name="Two")
        await one.two.add(two)
        await one.two.add(two)
        await two.one.add(one)
        self.assertEqual(await one.two, [two])
        self.assertEqual(await two.one, [one])

    async def test__add__two(self):
        one = await testmodels.M2MOne.create(name="One")
        two1 = await testmodels.M2MTwo.create(name="Two")
        two2 = await testmodels.M2MTwo.create(name="Two")
        await one.two.add(two1, two2)
        self.assertEqual(await one.two, [two1, two2])
        self.assertEqual(await two1.one, [one])
        self.assertEqual(await two2.one, [one])

    async def test__remove(self):
        one = await testmodels.M2MOne.create(name="One")
        two1 = await testmodels.M2MTwo.create(name="Two")
        two2 = await testmodels.M2MTwo.create(name="Two")
        await one.two.add(two1, two2)
        await one.two.remove(two1)
        self.assertEqual(await one.two, [two2])
        self.assertEqual(await two1.one, [])
        self.assertEqual(await two2.one, [one])

    async def test__remove__many(self):
        one = await testmodels.M2MOne.create(name="One")
        two1 = await testmodels.M2MTwo.create(name="Two1")
        two2 = await testmodels.M2MTwo.create(name="Two2")
        two3 = await testmodels.M2MTwo.create(name="Two3")
        await one.two.add(two1, two2, two3)
        await one.two.remove(two1, two2)
        self.assertEqual(await one.two, [two3])
        self.assertEqual(await two1.one, [])
        self.assertEqual(await two2.one, [])
        self.assertEqual(await two3.one, [one])

    async def test__remove__blank(self):
        one = await testmodels.M2MOne.create(name="One")
        with self.assertRaisesRegex(OperationalError, r"remove\(\) called on no instances"):
            await one.two.remove()

    async def test__clear(self):
        one = await testmodels.M2MOne.create(name="One")
        two1 = await testmodels.M2MTwo.create(name="Two")
        two2 = await testmodels.M2MTwo.create(name="Two")
        await one.two.add(two1, two2)
        await one.two.clear()
        self.assertEqual(await one.two, [])
        self.assertEqual(await two1.one, [])
        self.assertEqual(await two2.one, [])

    async def test__uninstantiated_add(self):
        one = testmodels.M2MOne(name="One")
        two = await testmodels.M2MTwo.create(name="Two")
        with self.assertRaisesRegex(
            OperationalError, r"You should first call .save\(\) on <M2MOne>"
        ):
            await one.two.add(two)

    async def test__add_uninstantiated(self):
        one = testmodels.M2MOne(name="One")
        two = await testmodels.M2MTwo.create(name="Two")
        with self.assertRaisesRegex(
            OperationalError, r"You should first call .save\(\) on <M2MOne>"
        ):
            await two.one.add(one)

    async def test_create_unique_index(self):
        message = "Parameter `create_unique_index` is deprecated! Use `unique` instead."
        with self.assertWarnsRegex(DeprecationWarning, message):
            field = ManyToManyField("models.Foo", create_unique_index=False)
        assert field.unique is False
        with self.assertWarnsRegex(DeprecationWarning, message):
            field = ManyToManyField("models.Foo", create_unique_index=False, unique=True)
        assert field.unique is False
        with self.assertWarnsRegex(DeprecationWarning, message):
            field = ManyToManyField("models.Foo", create_unique_index=True)
        assert field.unique is True
        with self.assertWarnsRegex(DeprecationWarning, message):
            field = ManyToManyField("models.Foo", create_unique_index=True, unique=False)
        assert field.unique is True
        field = ManyToManyField(
            "models.Group",
        )
        assert field.unique is True
        field = ManyToManyField(
            "models.Group",
            "user_group",
            "user_id",
            "group_id",
            "users",
            "CASCADE",
            True,
            False,
        )
        assert field.unique is False
