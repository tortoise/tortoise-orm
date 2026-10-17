from __future__ import annotations

import sys
from types import ModuleType

import pytest
import pytest_asyncio

from tests.testmodels import Signals
from tortoise import BaseDBAsyncClient, Model, fields
from tortoise.context import TortoiseContext
from tortoise.signals import Signals as SignalType
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


@pytest.fixture
def signal_models(monkeypatch):
    monkeypatch.setattr(Model, "_listeners", {signal: {} for signal in SignalType})

    class SignalBase(Model):
        name = fields.CharField(max_length=20)

        class Meta:
            abstract = True

    class SignalLeft(SignalBase):
        pass

    class SignalRight(SignalBase):
        pass

    class SignalChild(SignalLeft, SignalRight):
        pass

    class SignalOther(Model):
        pass

    return SignalBase, SignalLeft, SignalRight, SignalChild, SignalOther


@pytest.mark.asyncio
@pytest.mark.parametrize("signal", list(SignalType))
async def test_inherited_signal_listeners(signal_models, signal):
    base, left, right, child, other = signal_models
    calls = []
    instance = child(name="child")

    for model in (base, left, right, child):

        async def listener(sender, obj, *args, registered_model=model):
            calls.append((registered_model, sender, obj, args))

        model.register_listener(signal, listener)

    await instance._wait_for_listeners(signal, "argument")
    assert len(calls) == 4
    assert {call[0] for call in calls} == {base, left, right, child}
    assert all(call[1:] == (child, instance, ("argument",)) for call in calls)

    calls.clear()
    await other()._wait_for_listeners(signal, "argument")
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("signal", list(SignalType))
async def test_inherited_signal_listener_runs_once(signal_models, signal):
    base, left, right, child, _ = signal_models
    calls = []

    class Listener:
        __hash__ = None

        async def __call__(self, sender, instance, *args):
            calls.append(instance)

    listener = Listener()
    for model in (base, left, right, child):
        model.register_listener(signal, listener)

    instance = child(name="child")
    await instance._wait_for_listeners(signal)
    assert calls == [instance]


@pytest.mark.asyncio
async def test_inherited_signals_during_save_and_delete(signal_models, monkeypatch):
    base, _, _, child, other = signal_models
    calls = []

    for decorator in (pre_save, post_save, pre_delete, post_delete):

        async def listener(sender, instance, *args, event=decorator.__name__):
            calls.append((event, sender, instance))

        decorator(base)(listener)

    module = ModuleType("inherited_signal_models")
    module.__dict__["__models__"] = [child, other]
    monkeypatch.setitem(sys.modules, module.__name__, module)
    async with TortoiseContext() as ctx:
        await ctx.init(db_url="sqlite://:memory:", modules={"models": [module.__name__]})
        await ctx.generate_schemas()
        instance = await child.create(name="created")
        instance.name = "updated"
        await instance.save(update_fields=["name"])
        assert (await child.get(pk=instance.pk)).name == "updated"
        await instance.delete()
        assert await child.all().count() == 0
        unrelated = await other.create()
        await unrelated.delete()

    assert [call[0] for call in calls] == [
        "pre_save",
        "post_save",
        "pre_save",
        "post_save",
        "pre_delete",
        "post_delete",
    ]
    assert all(call[1:] == (child, instance) for call in calls)
