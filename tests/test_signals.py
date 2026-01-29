from __future__ import annotations

from tests.testmodels import Signals
from tortoise import BaseDBAsyncClient
from tortoise.contrib import test
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


class TestSignals(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.signal_save = await Signals.create(name="signal_save")
        self.signal_delete = await Signals.create(name="signal_delete")

        self.signal1 = await Signals.create(name="test1")
        self.signal2 = await Signals.create(name="test2")
        self.signal3 = await Signals.create(name="test3")
        self.signal4 = await Signals.create(name="test4")
        self.signal5 = await Signals.create(name="test5")
        self.signal6 = await Signals.create(name="test6")

    async def test_create(self):
        await Signals.create(name="test-create")
        signal5 = await Signals.get(pk=self.signal5.pk)
        signal6 = await Signals.get(pk=self.signal6.pk)
        self.assertEqual(signal5.name, "test_pre-save")
        self.assertEqual(signal6.name, "test_post-save")

    async def test_save(self):
        signal_save = await Signals.get(pk=self.signal_save.pk)
        signal_save.name = "test-save"
        await signal_save.save()

        signal1 = await Signals.get(pk=self.signal1.pk)
        signal2 = await Signals.get(pk=self.signal2.pk)

        self.assertEqual(signal1.name, "test_pre-save")
        self.assertEqual(signal2.name, "test_post-save")

    async def test_delete(self):
        signal_delete = await Signals.get(pk=self.signal_delete.pk)
        await signal_delete.delete()

        signal3 = await Signals.get(pk=self.signal3.pk)
        signal4 = await Signals.get(pk=self.signal4.pk)

        self.assertEqual(signal3.name, "test_pre-delete")
        self.assertEqual(signal4.name, "test_post-delete")
