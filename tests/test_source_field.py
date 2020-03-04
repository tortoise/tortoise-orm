"""
This module does a series of use tests on a non-source_field model,
  and then the EXACT same ones on a source_field'ed model.

This is to test that behaviour doesn't change when one defined source_field parameters.
"""
from tests.testmodels import SourceFields, StraightFields
from tortoise.contrib import test
from tortoise.expressions import F
from tortoise.functions import Trim


class StraightFieldTests(test.TestCase):
    def setUp(self) -> None:
        self.model = StraightFields

    async def test_get_all(self):
        obj1 = await self.model.create(chars="aaa")
        self.assertIsNotNone(obj1.eyedee, str(dir(obj1)))
        obj2 = await self.model.create(chars="bbb")

        objs = await self.model.all()
        self.assertEqual(objs, [obj1, obj2])

    async def test_get_by_pk(self):
        obj = await self.model.create(chars="aaa")
        obj1 = await self.model.get(eyedee=obj.eyedee)

        self.assertEqual(obj, obj1)

    async def test_get_by_chars(self):
        obj = await self.model.create(chars="aaa")
        obj1 = await self.model.get(chars="aaa")

        self.assertEqual(obj, obj1)

    async def test_get_fk_forward_fetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)

        obj2a = await self.model.get(eyedee=obj2.eyedee)
        await obj2a.fetch_related("fk")
        self.assertEqual(obj2, obj2a)
        self.assertEqual(obj1, obj2a.fk)

    async def test_get_fk_forward_prefetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)

        obj2a = await self.model.get(eyedee=obj2.eyedee).prefetch_related("fk")
        self.assertEqual(obj2, obj2a)
        self.assertEqual(obj1, obj2a.fk)

    async def test_get_fk_reverse_await(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        self.assertEqual(await obj1a.fkrev, [obj2, obj3])

    async def test_get_fk_reverse_filter(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        objs = await self.model.filter(fk=obj1)
        self.assertEqual(objs, [obj2, obj3])

    async def test_get_fk_reverse_async_for(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        objs = []
        async for obj in obj1a.fkrev:
            objs.append(obj)
        self.assertEqual(objs, [obj2, obj3])

    async def test_get_fk_reverse_fetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        await obj1a.fetch_related("fkrev")
        self.assertEqual(list(obj1a.fkrev), [obj2, obj3])

    async def test_get_fk_reverse_prefetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee).prefetch_related("fkrev")
        self.assertEqual(list(obj1a.fkrev), [obj2, obj3])

    async def test_get_m2m_forward_await(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj2a = await self.model.get(eyedee=obj2.eyedee)
        self.assertEqual(await obj2a.rel_from, [obj1])

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        self.assertEqual(await obj1a.rel_to, [obj2])

    async def test_get_m2m_reverse_await(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj2.rel_from.add(obj1)

        obj2a = await self.model.get(pk=obj2.eyedee)
        self.assertEqual(await obj2a.rel_from, [obj1])

        obj1a = await self.model.get(eyedee=obj1.pk)
        self.assertEqual(await obj1a.rel_to, [obj2])

    async def test_get_m2m_filter(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        rel_froms = await self.model.filter(rel_from=obj1)
        self.assertEqual(rel_froms, [obj2])

        rel_tos = await self.model.filter(rel_to=obj2)
        self.assertEqual(rel_tos, [obj1])

    async def test_get_m2m_forward_fetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj2a = await self.model.get(eyedee=obj2.eyedee)
        await obj2a.fetch_related("rel_from")
        self.assertEqual(list(obj2a.rel_from), [obj1])

    async def test_get_m2m_reverse_fetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        await obj1a.fetch_related("rel_to")
        self.assertEqual(list(obj1a.rel_to), [obj2])

    async def test_get_m2m_forward_prefetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj2a = await self.model.get(eyedee=obj2.eyedee).prefetch_related("rel_from")
        self.assertEqual(list(obj2a.rel_from), [obj1])

    async def test_get_m2m_reverse_prefetch_related(self):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj1a = await self.model.get(eyedee=obj1.eyedee).prefetch_related("rel_to")
        self.assertEqual(list(obj1a.rel_to), [obj2])

    async def test_f_expression(self):
        obj1 = await self.model.create(chars="aaa")
        await self.model.filter(eyedee=obj1.eyedee).update(chars=F("blip"))
        obj2 = await self.model.get(eyedee=obj1.eyedee)
        self.assertEqual(obj2.chars, "BLIP")

    async def test_function(self):
        obj1 = await self.model.create(chars="  aaa ")
        await self.model.filter(eyedee=obj1.eyedee).update(chars=Trim("chars"))
        obj2 = await self.model.get(eyedee=obj1.eyedee)
        self.assertEqual(obj2.chars, "aaa")


class SourceFieldTests(StraightFieldTests):
    def setUp(self) -> None:
        self.model = SourceFields  # type: ignore
