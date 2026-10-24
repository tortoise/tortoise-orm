import pytest

from tests.testmodels import Tournament


@pytest.mark.asyncio
@pytest.mark.parametrize("projection", ["values", "values_list", "flat"])
async def test_projected_query_honors_zero_limit(db, projection):
    await Tournament.create(name="example")
    query = Tournament.all().limit(0)
    assert await query == []
    if projection == "values":
        projected = query.values("id")
    else:
        projected = query.values_list("id", flat=projection == "flat")
    assert await projected == []
