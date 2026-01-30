"""
This module does a series of use tests on a non-source_field model,
  and then the EXACT same ones on a source_field'ed model.

This is to test that behaviour doesn't change when one defined source_field parameters.
"""

import pytest

from tests.testmodels import NumberSourceField, SourceFields, StraightFields
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
from tortoise.expressions import F, Q
from tortoise.functions import Coalesce, Count, Length, Lower, Trim, Upper


# Helper function to sort model instances by pk
def sort_by_pk(items):
    return sorted(items, key=lambda x: x.pk)


class TestStraightFields:
    """Tests for StraightFields model."""

    model = StraightFields

    @pytest.mark.asyncio
    async def test_get_all(self, db):
        obj1 = await self.model.create(chars="aaa")
        assert obj1.eyedee is not None, str(dir(obj1))
        obj2 = await self.model.create(chars="bbb")

        objs = await self.model.all()
        assert sort_by_pk(objs) == sort_by_pk([obj1, obj2])

    @pytest.mark.asyncio
    async def test_get_by_pk(self, db):
        obj = await self.model.create(chars="aaa")
        obj1 = await self.model.get(eyedee=obj.eyedee)

        assert obj == obj1

    @pytest.mark.asyncio
    async def test_get_by_chars(self, db):
        obj = await self.model.create(chars="aaa")
        obj1 = await self.model.get(chars="aaa")

        assert obj == obj1

    @pytest.mark.asyncio
    async def test_get_fk_forward_fetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)

        obj2a = await self.model.get(eyedee=obj2.eyedee)
        await obj2a.fetch_related("fk")
        assert obj2 == obj2a
        assert obj1 == obj2a.fk

    @pytest.mark.asyncio
    async def test_get_fk_forward_prefetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)

        obj2a = await self.model.get(eyedee=obj2.eyedee).prefetch_related("fk")
        assert obj2 == obj2a
        assert obj1 == obj2a.fk

    @pytest.mark.asyncio
    async def test_get_fk_reverse_await(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        assert sort_by_pk(await obj1a.fkrev) == sort_by_pk([obj2, obj3])

    @pytest.mark.asyncio
    async def test_get_fk_reverse_filter(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        objs = await self.model.filter(fk=obj1)
        assert sort_by_pk(objs) == sort_by_pk([obj2, obj3])

    @pytest.mark.asyncio
    async def test_get_fk_reverse_async_for(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        objs = []
        async for obj in obj1a.fkrev:
            objs.append(obj)
        assert sort_by_pk(objs) == sort_by_pk([obj2, obj3])

    @pytest.mark.asyncio
    async def test_get_fk_reverse_fetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        await obj1a.fetch_related("fkrev")
        assert sort_by_pk(list(obj1a.fkrev)) == sort_by_pk([obj2, obj3])

    @pytest.mark.asyncio
    async def test_get_fk_reverse_prefetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb", fk=obj1)
        obj3 = await self.model.create(chars="ccc", fk=obj1)

        obj1a = await self.model.get(eyedee=obj1.eyedee).prefetch_related("fkrev")
        assert sort_by_pk(list(obj1a.fkrev)) == sort_by_pk([obj2, obj3])

    @pytest.mark.asyncio
    async def test_get_m2m_forward_await(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj2a = await self.model.get(eyedee=obj2.eyedee)
        assert await obj2a.rel_from == [obj1]

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        assert await obj1a.rel_to == [obj2]

    @pytest.mark.asyncio
    async def test_get_m2m_reverse_await(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj2.rel_from.add(obj1)

        obj2a = await self.model.get(pk=obj2.eyedee)
        assert await obj2a.rel_from == [obj1]

        obj1a = await self.model.get(eyedee=obj1.pk)
        assert await obj1a.rel_to == [obj2]

    @pytest.mark.asyncio
    async def test_get_m2m_filter(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        rel_froms = await self.model.filter(rel_from=obj1)
        assert rel_froms == [obj2]

        rel_tos = await self.model.filter(rel_to=obj2)
        assert rel_tos == [obj1]

    @pytest.mark.asyncio
    async def test_get_m2m_forward_fetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj2a = await self.model.get(eyedee=obj2.eyedee)
        await obj2a.fetch_related("rel_from")
        assert list(obj2a.rel_from) == [obj1]

    @pytest.mark.asyncio
    async def test_get_m2m_reverse_fetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj1a = await self.model.get(eyedee=obj1.eyedee)
        await obj1a.fetch_related("rel_to")
        assert list(obj1a.rel_to) == [obj2]

    @pytest.mark.asyncio
    async def test_get_m2m_forward_prefetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj2a = await self.model.get(eyedee=obj2.eyedee).prefetch_related("rel_from")
        assert list(obj2a.rel_from) == [obj1]

    @pytest.mark.asyncio
    async def test_get_m2m_reverse_prefetch_related(self, db):
        obj1 = await self.model.create(chars="aaa")
        obj2 = await self.model.create(chars="bbb")
        await obj1.rel_to.add(obj2)

        obj1a = await self.model.get(eyedee=obj1.eyedee).prefetch_related("rel_to")
        assert list(obj1a.rel_to) == [obj2]

    @pytest.mark.asyncio
    async def test_values_reverse_relation(self, db):
        obj1 = await self.model.create(chars="aaa")
        await self.model.create(chars="bbb", fk=obj1)

        obj1a = await self.model.filter(chars="aaa").values("fkrev__chars")
        assert obj1a[0]["fkrev__chars"] == "bbb"

    @pytest.mark.asyncio
    async def test_f_expression(self, db):
        obj1 = await self.model.create(chars="aaa")
        await self.model.filter(eyedee=obj1.eyedee).update(chars=F("blip"))
        obj2 = await self.model.get(eyedee=obj1.eyedee)
        assert obj2.chars == "BLIP"

    @pytest.mark.asyncio
    async def test_function(self, db):
        obj1 = await self.model.create(chars="  aaa ")
        await self.model.filter(eyedee=obj1.eyedee).update(chars=Trim("chars"))
        obj2 = await self.model.get(eyedee=obj1.eyedee)
        assert obj2.chars == "aaa"

    @pytest.mark.asyncio
    async def test_aggregation_with_filter(self, db):
        obj1 = await self.model.create(chars="aaa")
        await self.model.create(chars="bbb", fk=obj1)
        await self.model.create(chars="ccc", fk=obj1)

        obj = (
            await self.model.filter(chars="aaa")
            .annotate(
                all=Count("fkrev", _filter=Q(chars="aaa")),
                one=Count("fkrev", _filter=Q(fkrev__chars="bbb")),
                no=Count("fkrev", _filter=Q(fkrev__chars="aaa")),
            )
            .first()
        )

        assert obj.all == 2
        assert obj.one == 1
        assert obj.no == 0

    @pytest.mark.asyncio
    async def test_filter_by_aggregation_field_coalesce(self, db):
        await self.model.create(chars="aaa", nullable="null")
        await self.model.create(chars="bbb")
        objs = await self.model.annotate(null=Coalesce("nullable", "null")).filter(null="null")

        assert len(objs) == 2
        assert {(o.chars, o.null) for o in objs} == {("aaa", "null"), ("bbb", "null")}

    @pytest.mark.asyncio
    async def test_filter_by_aggregation_field_count(self, db):
        await self.model.create(chars="aaa")
        await self.model.create(chars="bbb")
        obj = await self.model.annotate(chars_count=Count("chars")).filter(
            chars_count=1, chars="aaa"
        )

        assert len(obj) == 1
        assert obj[0].chars == "aaa"

    @test.requireCapability(dialect=NotEQ("mssql"))
    @pytest.mark.asyncio
    async def test_filter_by_aggregation_field_length(self, db):
        await self.model.create(chars="aaa")
        await self.model.create(chars="bbbbb")
        obj = await self.model.annotate(chars_length=Length("chars")).filter(chars_length=3)

        assert len(obj) == 1
        assert obj[0].chars_length == 3

    @pytest.mark.asyncio
    async def test_filter_by_aggregation_field_lower(self, db):
        await self.model.create(chars="AaA")
        obj = await self.model.annotate(chars_lower=Lower("chars")).filter(chars_lower="aaa")

        assert len(obj) == 1
        assert obj[0].chars_lower == "aaa"

    @pytest.mark.asyncio
    async def test_filter_by_aggregation_field_trim(self, db):
        await self.model.create(chars="   aaa   ")
        obj = await self.model.annotate(chars_trim=Trim("chars")).filter(chars_trim="aaa")

        assert len(obj) == 1
        assert obj[0].chars_trim == "aaa"

    @pytest.mark.asyncio
    async def test_filter_by_aggregation_field_upper(self, db):
        await self.model.create(chars="aAa")
        obj = await self.model.annotate(chars_upper=Upper("chars")).filter(chars_upper="AAA")

        assert len(obj) == 1
        assert obj[0].chars_upper == "AAA"

    @pytest.mark.asyncio
    async def test_values_by_fk(self, db):
        obj1 = await self.model.create(chars="aaa")
        await self.model.create(chars="bbb", fk=obj1)

        obj = await self.model.filter(chars="bbb").values("fk__chars")
        assert obj == [{"fk__chars": "aaa"}]

    @pytest.mark.asyncio
    async def test_filter_with_field_f(self, db):
        obj = await self.model.create(chars="a")
        ret_obj = await self.model.filter(eyedee=F("eyedee")).first()
        assert obj == ret_obj

        ret_obj = await self.model.filter(eyedee__lt=F("eyedee") + 1).first()
        assert obj == ret_obj

    @pytest.mark.asyncio
    async def test_filter_with_field_f_annotation(self, db):
        obj = await self.model.create(chars="a")
        ret_obj = (
            await self.model.annotate(eyedee_a=F("eyedee")).filter(eyedee=F("eyedee_a")).first()
        )
        assert obj == ret_obj

        ret_obj = (
            await self.model.annotate(eyedee_a=F("eyedee") + 1)
            .filter(eyedee__lt=F("eyedee_a"))
            .first()
        )
        assert obj == ret_obj

    @pytest.mark.asyncio
    async def test_group_by(self, db):
        await self.model.create(chars="aaa", blip="a")
        await self.model.create(chars="aaa", blip="b")
        await self.model.create(chars="bbb")

        objs = (
            await self.model.annotate(chars_count=Count("chars"))
            .group_by("chars")
            .order_by("chars")
            .values("chars", "chars_count")
        )
        assert objs == [{"chars": "aaa", "chars_count": 2}, {"chars": "bbb", "chars_count": 1}]


class TestSourceFields(TestStraightFields):
    """Tests for SourceFields model (same tests as StraightFields)."""

    model = SourceFields  # type: ignore[assignment]


class TestNumberSourceField:
    """Tests for NumberSourceField model."""

    model = NumberSourceField

    @pytest.mark.asyncio
    async def test_f_expression_save(self, db):
        obj1 = await self.model.create()
        obj1.number = F("number") + 1
        await obj1.save()

    @pytest.mark.asyncio
    async def test_f_expression_save_update_fields(self, db):
        obj1 = await self.model.create()
        obj1.number = F("number") + 1
        await obj1.save(update_fields=["number"])
