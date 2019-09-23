import uuid

from tests.testmodels import (
    CharFkRelatedModel,
    CharM2MRelatedModel,
    CharPkModel,
    ImplicitPkModel,
    UUIDFkRelatedModel,
    UUIDM2MRelatedModel,
    UUIDPkModel,
)
from tortoise.contrib import test


class TestQueryset(test.TestCase):
    async def test_implicit_pk(self):
        instance = await ImplicitPkModel.create(value="test")
        self.assertTrue(instance.id)
        self.assertEqual(instance.pk, instance.id)

    async def test_uuid_pk(self):
        value = uuid.uuid4()
        await UUIDPkModel.create(id=value)

        instance2 = await UUIDPkModel.get(id=value)
        self.assertEqual(instance2.id, value)
        self.assertEqual(instance2.pk, value)

    async def test_uuid_pk_default(self):
        instance1 = await UUIDPkModel.create()
        self.assertIsInstance(instance1.id, uuid.UUID)
        self.assertEqual(instance1.pk, instance1.pk)

        instance2 = await UUIDPkModel.get(id=instance1.id)
        self.assertEqual(instance2.id, instance1.id)
        self.assertEqual(instance2.pk, instance1.id)

    async def test_uuid_pk_fk(self):
        value = uuid.uuid4()
        instance = await UUIDPkModel.create(id=value)
        instance2 = await UUIDPkModel.create(id=uuid.uuid4())
        await UUIDFkRelatedModel.create(model=instance2)

        related_instance = await UUIDFkRelatedModel.create(model=instance)
        self.assertEqual(related_instance.model_id, value)

        related_instance = await UUIDFkRelatedModel.filter(model=instance).first()
        self.assertEqual(related_instance.model_id, value)

        related_instance = await UUIDFkRelatedModel.filter(model_id=value).first()
        self.assertEqual(related_instance.model_id, value)

        await related_instance.fetch_related("model")
        self.assertEqual(related_instance.model, instance)

        await instance.fetch_related("children")
        self.assertEqual(instance.children[0], related_instance)

    async def test_uuid_m2m(self):
        value = uuid.uuid4()
        instance = await UUIDPkModel.create(id=value)
        instance2 = await UUIDPkModel.create(id=uuid.uuid4())

        related_instance = await UUIDM2MRelatedModel.create()
        related_instance2 = await UUIDM2MRelatedModel.create()

        await instance.peers.add(related_instance)
        await related_instance2.models.add(instance, instance2)

        await instance.fetch_related("peers")
        self.assertEqual(len(instance.peers), 2)
        self.assertEqual(set(instance.peers), {related_instance, related_instance2})

        await related_instance.fetch_related("models")
        self.assertEqual(len(related_instance.models), 1)
        self.assertEqual(related_instance.models[0], instance)

        await related_instance2.fetch_related("models")
        self.assertEqual(len(related_instance2.models), 2)
        self.assertEqual({m.pk for m in related_instance2.models}, {instance.pk, instance2.pk})

        related_instance_list = await UUIDM2MRelatedModel.filter(models=instance2)
        self.assertEqual(len(related_instance_list), 1)
        self.assertEqual(related_instance_list[0], related_instance2)

        related_instance_list = await UUIDM2MRelatedModel.filter(models__in=[instance2])
        self.assertEqual(len(related_instance_list), 1)
        self.assertEqual(related_instance_list[0], related_instance2)

    async def test_char_pk(self):
        value = "Da-PK"
        await CharPkModel.create(id=value)

        instance2 = await CharPkModel.get(id=value)
        self.assertEqual(instance2.id, value)
        self.assertEqual(instance2.pk, value)

    async def test_char_pk_fk(self):
        value = "Da-PK-for-FK"
        instance = await CharPkModel.create(id=value)
        instance2 = await CharPkModel.create(id=uuid.uuid4())
        await CharFkRelatedModel.create(model=instance2)

        related_instance = await CharFkRelatedModel.create(model=instance)
        self.assertEqual(related_instance.model_id, value)

        related_instance = await CharFkRelatedModel.filter(model=instance).first()
        self.assertEqual(related_instance.model_id, value)

        related_instance = await CharFkRelatedModel.filter(model_id=value).first()
        self.assertEqual(related_instance.model_id, value)

        await instance.fetch_related("children")
        self.assertEqual(instance.children[0], related_instance)

    async def test_char_m2m(self):
        value = "Da-PK-for-M2M"
        instance = await CharPkModel.create(id=value)
        instance2 = await CharPkModel.create(id=uuid.uuid4())

        related_instance = await CharM2MRelatedModel.create()
        related_instance2 = await CharM2MRelatedModel.create()

        await instance.peers.add(related_instance)
        await related_instance2.models.add(instance, instance2)

        await related_instance.fetch_related("models")
        self.assertEqual(len(related_instance.models), 1)
        self.assertEqual(related_instance.models[0], instance)

        await related_instance2.fetch_related("models")
        self.assertEqual(len(related_instance2.models), 2)
        self.assertEqual({m.pk for m in related_instance2.models}, {instance.pk, instance2.pk})

        related_instance_list = await CharM2MRelatedModel.filter(models=instance2)
        self.assertEqual(len(related_instance_list), 1)
        self.assertEqual(related_instance_list[0], related_instance2)

        related_instance_list = await CharM2MRelatedModel.filter(models__in=[instance2])
        self.assertEqual(len(related_instance_list), 1)
        self.assertEqual(related_instance_list[0], related_instance2)
