from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
import pytz
from pypika_tortoise.terms import Function as PupikaFunction

from tests.testmodels import (
    Currency,
    DatetimeFields,
    DefaultUpdate,
    EnumFields,
    Event,
    IntFields,
    JSONFields,
    Reporter,
    Service,
    SmallIntFields,
    SourceFieldPk,
    Tournament,
    UUIDFields,
)
from tortoise import timezone
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import In, NotEQ
from tortoise.expressions import Case, F, Q, Subquery, When
from tortoise.functions import Function, Upper


@pytest.mark.asyncio
async def test_update(db):
    await Tournament.create(name="1")
    await Tournament.create(name="3")
    rows_affected = await Tournament.all().update(name="2")
    assert rows_affected == 2

    tournament = await Tournament.first()
    assert tournament.name == "2"


@pytest.mark.asyncio
async def test_bulk_update(db):
    objs = [await Tournament.create(name="1"), await Tournament.create(name="2")]
    objs[0].name = "0"
    objs[1].name = "1"
    rows_affected = await Tournament.bulk_update(objs, fields=["name"], batch_size=100)
    assert rows_affected == 2
    assert (await Tournament.get(pk=objs[0].pk)).name == "0"
    assert (await Tournament.get(pk=objs[1].pk)).name == "1"


@pytest.mark.asyncio
async def test_bulk_update_datetime(db):
    objs = [
        await DatetimeFields.create(datetime=datetime(2021, 1, 1, tzinfo=pytz.utc)),
        await DatetimeFields.create(datetime=datetime(2021, 1, 1, tzinfo=pytz.utc)),
    ]
    t0 = datetime(2021, 1, 2, tzinfo=pytz.utc)
    t1 = datetime(2021, 1, 3, tzinfo=pytz.utc)
    objs[0].datetime = t0
    objs[1].datetime = t1
    rows_affected = await DatetimeFields.bulk_update(objs, fields=["datetime"])
    assert rows_affected == 2
    assert (await DatetimeFields.get(pk=objs[0].pk)).datetime == t0
    assert (await DatetimeFields.get(pk=objs[1].pk)).datetime == t1


@pytest.mark.asyncio
async def test_bulk_update_pk_non_id(db):
    tournament = await Tournament.create(name="")
    events = [
        await Event.create(name="1", tournament=tournament),
        await Event.create(name="2", tournament=tournament),
    ]
    events[0].name = "3"
    events[1].name = "4"
    rows_affected = await Event.bulk_update(events, fields=["name"])
    assert rows_affected == 2
    assert (await Event.get(pk=events[0].pk)).name == events[0].name
    assert (await Event.get(pk=events[1].pk)).name == events[1].name


@pytest.mark.asyncio
async def test_bulk_update_pk_uuid(db):
    objs = [
        await UUIDFields.create(data=uuid.uuid4()),
        await UUIDFields.create(data=uuid.uuid4()),
    ]
    objs[0].data = uuid.uuid4()
    objs[1].data = uuid.uuid4()
    rows_affected = await UUIDFields.bulk_update(objs, fields=["data"])
    assert rows_affected == 2
    assert (await UUIDFields.get(pk=objs[0].pk)).data == objs[0].data
    assert (await UUIDFields.get(pk=objs[1].pk)).data == objs[1].data


@pytest.mark.asyncio
async def test_bulk_renamed_pk_source_field(db):
    objs = [
        await SourceFieldPk.create(name="Model 1"),
        await SourceFieldPk.create(name="Model 2"),
    ]
    objs[0].name = "Model 3"
    objs[1].name = "Model 4"
    rows_affected = await SourceFieldPk.bulk_update(objs, fields=["name"])
    assert rows_affected == 2
    assert (await SourceFieldPk.get(pk=objs[0].pk)).name == objs[0].name
    assert (await SourceFieldPk.get(pk=objs[1].pk)).name == objs[1].name


@pytest.mark.asyncio
async def test_bulk_update_json_value(db):
    objs = [
        await JSONFields.create(data={}),
        await JSONFields.create(data={}),
    ]
    objs[0].data = [0]
    objs[1].data = {"a": 1}
    rows_affected = await JSONFields.bulk_update(objs, fields=["data"])
    assert rows_affected == 2
    assert (await JSONFields.get(pk=objs[0].pk)).data == objs[0].data
    assert (await JSONFields.get(pk=objs[1].pk)).data == objs[1].data


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_update_smallint_none(db):
    objs = [
        await SmallIntFields.create(smallintnum=1, smallintnum_null=1),
        await SmallIntFields.create(smallintnum=2, smallintnum_null=2),
    ]
    objs[0].smallintnum_null = None
    objs[1].smallintnum_null = None
    rows_affected = await SmallIntFields.bulk_update(objs, fields=["smallintnum_null"])
    assert rows_affected == 2
    assert (await SmallIntFields.get(pk=objs[0].pk)).smallintnum_null is None
    assert (await SmallIntFields.get(pk=objs[1].pk)).smallintnum_null is None


@pytest.mark.asyncio
async def test_bulk_update_custom_field(db):
    objs = [
        await EnumFields.create(service=Service.python_programming, currency=Currency.EUR),
        await EnumFields.create(service=Service.database_design, currency=Currency.USD),
    ]
    objs[0].currency = Currency.USD
    objs[1].service = Service.system_administration
    rows_affected = await EnumFields.bulk_update(objs, fields=["service", "currency"])
    assert rows_affected == 2
    assert (await EnumFields.get(pk=objs[0].pk)).currency == Currency.USD
    assert (await EnumFields.get(pk=objs[1].pk)).service == Service.system_administration


@pytest.mark.asyncio
async def test_update_auto_now(db):
    obj = await DefaultUpdate.create()

    updated_at = timezone.now() - timedelta(days=1)
    await DefaultUpdate.filter(pk=obj.pk).update(updated_at=updated_at)

    obj1 = await DefaultUpdate.get(pk=obj.pk)
    assert obj1.updated_at.date() == updated_at.date()


@pytest.mark.asyncio
async def test_update_relation(db):
    tournament_first = await Tournament.create(name="1")
    tournament_second = await Tournament.create(name="2")

    await Event.create(name="1", tournament=tournament_first)
    await Event.all().update(tournament=tournament_second)
    event = await Event.first()
    assert event.tournament_id == tournament_second.id


@requireCapability(dialect=In("mysql", "sqlite"))
@pytest.mark.asyncio
async def test_update_with_custom_function(db):
    class JsonSet(Function):
        class PypikaJsonSet(PupikaFunction):
            def __init__(self, field: F, expression: str, value: Any):
                super().__init__("JSON_SET", field, expression, value)

        database_func = PypikaJsonSet

    json = await JSONFields.create(data={})
    assert json.data_default == {"a": 1}

    json.data_default = JsonSet(F("data_default"), "$.a", 2)
    await json.save()

    json_update = await JSONFields.get(pk=json.pk)
    assert json_update.data_default == {"a": 2}

    await JSONFields.filter(pk=json.pk).update(data_default=JsonSet(F("data_default"), "$.a", 3))
    json_update = await JSONFields.get(pk=json.pk)
    assert json_update.data_default == {"a": 3}


@pytest.mark.asyncio
async def test_refresh_from_db(db):
    int_field = await IntFields.create(intnum=1, intnum_null=2)
    int_field_in_db = await IntFields.get(pk=int_field.pk)
    int_field_in_db.intnum = F("intnum") + 1
    await int_field_in_db.save(update_fields=["intnum"])
    assert int_field_in_db.intnum != 2
    assert int_field_in_db.intnum_null == 2

    await int_field_in_db.refresh_from_db(fields=["intnum"])
    assert int_field_in_db.intnum == 2
    assert int_field_in_db.intnum_null == 2

    int_field_in_db.intnum = F("intnum") + 1
    await int_field_in_db.save()
    assert int_field_in_db.intnum != 3
    assert int_field_in_db.intnum_null == 2

    await int_field_in_db.refresh_from_db()
    assert int_field_in_db.intnum == 3
    assert int_field_in_db.intnum_null == 2


@requireCapability(support_update_limit_order_by=True)
@pytest.mark.asyncio
async def test_update_with_limit_ordering(db):
    await Tournament.create(name="1")
    t2 = await Tournament.create(name="1")
    await Tournament.filter(name="1").limit(1).order_by("-id").update(name="2")
    assert (await Tournament.get(pk=t2.pk)).name == "2"
    assert await Tournament.filter(name="1").count() == 1


# tortoise-pypika does not translate ** to POWER in MSSQL
@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_update_with_case_when_and_f(db):
    event1 = await IntFields.create(intnum=1)
    event2 = await IntFields.create(intnum=2)
    event3 = await IntFields.create(intnum=3)
    await (
        IntFields.all()
        .annotate(
            intnum_updated=Case(
                When(
                    Q(intnum=1),
                    then=F("intnum") + 1,
                ),
                When(
                    Q(intnum=2),
                    then=F("intnum") * 2,
                ),
                default=F("intnum") ** 3,
            )
        )
        .update(intnum=F("intnum_updated"))
    )

    for e in [event1, event2, event3]:
        await e.refresh_from_db()
    assert event1.intnum == 2
    assert event2.intnum == 4
    assert event3.intnum == 27


@pytest.mark.asyncio
async def test_update_with_function_annotation(db):
    tournament = await Tournament.create(name="aaa")
    await (
        Tournament.filter(pk=tournament.pk)
        .annotate(
            upped_name=Upper(F("name")),
        )
        .update(name=F("upped_name"))
    )
    assert (await Tournament.get(pk=tournament.pk)).name == "AAA"


@pytest.mark.asyncio
async def test_update_with_filter_subquery(db):
    t1 = await Tournament.create(name="1")
    r1 = await Reporter.create(name="1")
    e1 = await Event.create(name="1", tournament=t1, reporter=r1)

    # NOTE: this is intentionally written with Subquery and known PKs to test
    # whether subqueries are parameterized correctly.
    await Event.filter(
        tournament_id__in=Subquery(Tournament.filter(pk__in=[t1.pk]).values("id")),
        reporter_id__in=Subquery(Reporter.filter(pk__in=[r1.pk]).values("id")),
    ).update(token="hello_world")

    await e1.refresh_from_db(fields=["token"])
    assert e1.token == "hello_world"
