import asyncio
import random

from tests.testmodels import BenchmarkModel
from tortoise.contrib.test import _restore_default


def test_get(benchmark):
    _restore_default()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    minid = maxid = -1

    async def _setup():
        nonlocal minid, maxid
        for _ in range(100):
            o = await BenchmarkModel.create(level=random.randint(0, 100), text="test")
            minid = min(minid, o.id) if minid != -1 else o.id
            maxid = max(maxid, o.id) if maxid != -1 else o.id

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkModel.get(id=random.randint(minid, maxid))

        loop.run_until_complete(_bench())
