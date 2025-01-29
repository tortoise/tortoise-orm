import asyncio

from tests.testmodels import Event


def test_relations_values_related_m2m(benchmark, create_team_with_participants):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await Event.all().values("participants__name")

        loop.run_until_complete(_bench())
