from __future__ import annotations

import pytest
import pytest_asyncio

from tests.testmodels import Signals
from tortoise import BaseDBAsyncClient
from tortoise.signals import post_delete, post_save, pre_delete, pre_save


@pre_save(Signals)
async def signal_pre_save(
    sender: type[Signals], instance: Signals, using_db, update_fields
) -> None:
    await Signals.filter(name="test1").update(name="test_pre-save")
    await Signals.filter(name="test5").update(name="test_pre-save")


@post_save(Signals)
async def signal_post_save(
    sender: type[Signals],
    instance: Signals,
    created: bool,
    using_db: BaseDBAsyncClient | None,
    update_fields: list,
) -> None:
    await Signals.filter(name="test2").update(name="test_post-save")
    await Signals.filter(name="test6").update(name="test_post-save")


@pre_delete(Signals)
async def signal_pre_delete(
    sender: type[Signals], instance: Signals, using_db: BaseDBAsyncClient | None
) -> None:
    await Signals.filter(name="test3").update(name="test_pre-delete")


@post_delete(Signals)
async def signal_post_delete(
    sender: type[Signals], instance: Signals, using_db: BaseDBAsyncClient | None
) -> None:
    await Signals.filter(name="test4").update(name="test_post-delete")


@pytest_asyncio.fixture
async def signals_data(db):
    """Set up test data for signal tests."""
    signal_save = await Signals.create(name="signal_save")
    signal_delete = await Signals.create(name="signal_delete")

    signal1 = await Signals.create(name="test1")
    signal2 = await Signals.create(name="test2")
    signal3 = await Signals.create(name="test3")
    signal4 = await Signals.create(name="test4")
    signal5 = await Signals.create(name="test5")
    signal6 = await Signals.create(name="test6")

    return {
        "signal_save": signal_save,
        "signal_delete": signal_delete,
        "signal1": signal1,
        "signal2": signal2,
        "signal3": signal3,
        "signal4": signal4,
        "signal5": signal5,
        "signal6": signal6,
    }


@pytest.mark.asyncio
async def test_create(signals_data):
    await Signals.create(name="test-create")
    signal5 = await Signals.get(pk=signals_data["signal5"].pk)
    signal6 = await Signals.get(pk=signals_data["signal6"].pk)
    assert signal5.name == "test_pre-save"
    assert signal6.name == "test_post-save"


@pytest.mark.asyncio
async def test_save(signals_data):
    signal_save = await Signals.get(pk=signals_data["signal_save"].pk)
    signal_save.name = "test-save"
    await signal_save.save()

    signal1 = await Signals.get(pk=signals_data["signal1"].pk)
    signal2 = await Signals.get(pk=signals_data["signal2"].pk)

    assert signal1.name == "test_pre-save"
    assert signal2.name == "test_post-save"


@pytest.mark.asyncio
async def test_delete(signals_data):
    signal_delete = await Signals.get(pk=signals_data["signal_delete"].pk)
    await signal_delete.delete()

    signal3 = await Signals.get(pk=signals_data["signal3"].pk)
    signal4 = await Signals.get(pk=signals_data["signal4"].pk)

    assert signal3.name == "test_pre-delete"
    assert signal4.name == "test_post-delete"
