from tests.testmodels import SourceFields, StraightFields
from tortoise.contrib import test
from tortoise.exceptions import IncompleteInstanceError


class TestOnlyStraight(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.model = StraightFields
        self.instance = await self.model.create(chars="Test")

    async def test_get(self):
        instance_part = await self.model.get(chars="Test").only("chars", "blip")

        self.assertEqual(instance_part.chars, "Test")
        with self.assertRaises(AttributeError):
            _ = instance_part.nullable

    async def test_filter(self):
        instances = await self.model.filter(chars="Test").only("chars", "blip")

        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].chars, "Test")
        with self.assertRaises(AttributeError):
            _ = instances[0].nullable

    async def test_first(self):
        instance_part = await self.model.filter(chars="Test").only("chars", "blip").first()

        self.assertEqual(instance_part.chars, "Test")
        with self.assertRaises(AttributeError):
            _ = instance_part.nullable

    async def test_save(self):
        instance_part = await self.model.get(chars="Test").only("chars", "blip")

        with self.assertRaisesRegex(IncompleteInstanceError, " is a partial model"):
            await instance_part.save()

    async def test_partial_save(self):
        instance_part = await self.model.get(chars="Test").only("chars", "blip")

        with self.assertRaisesRegex(IncompleteInstanceError, "Partial update not available"):
            await instance_part.save(update_fields=["chars"])

    async def test_partial_save_with_pk_wrong_field(self):
        instance_part = await self.model.get(chars="Test").only("chars", "eyedee")

        with self.assertRaisesRegex(IncompleteInstanceError, "field 'nullable' is not available"):
            await instance_part.save(update_fields=["nullable"])

    async def test_partial_save_with_pk(self):
        instance_part = await self.model.get(chars="Test").only("chars", "eyedee")

        instance_part.chars = "Test1"
        await instance_part.save(update_fields=["chars"])

        instance2 = await self.model.get(pk=self.instance.pk)
        self.assertEqual(instance2.chars, "Test1")


class TestOnlySource(TestOnlyStraight):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.model = SourceFields  # type: ignore
        self.instance = await self.model.create(chars="Test")
