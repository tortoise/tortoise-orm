"""
Tests for truncate_all_models() and _topological_sort_models().

Verifies FK-aware truncation ordering and the PostgreSQL TRUNCATE CASCADE path.
"""

import pytest

from tests.testmodels import Employee, Event, MinRelation, Reporter, Team, Tournament
from tortoise import Tortoise
from tortoise.contrib.test import _topological_sort_models, truncate_all_models

# ---------------------------------------------------------------------------
# _topological_sort_models — unit tests on real model metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_topological_sort_children_before_parents(db):
    """Event (FK→Tournament) must come before Tournament in delete order."""
    sorted_models = _topological_sort_models([Tournament, Event])
    assert sorted_models.index(Event) < sorted_models.index(Tournament)


@pytest.mark.asyncio
async def test_topological_sort_input_order_independent(db):
    """Result must be the same regardless of input order."""
    order_a = _topological_sort_models([Tournament, Event])
    order_b = _topological_sort_models([Event, Tournament])
    assert order_a == order_b


@pytest.mark.asyncio
async def test_topological_sort_self_referential_fk(db):
    """Self-referential FK (Employee→Employee) must not cause infinite loop."""
    result = _topological_sort_models([Employee])
    assert result == [Employee]


@pytest.mark.asyncio
async def test_topological_sort_no_fk_models(db):
    """Models without FK relationships are still included."""
    result = _topological_sort_models([Team])
    assert result == [Team]


@pytest.mark.asyncio
async def test_topological_sort_all_models(db):
    """Sorting all registered models succeeds and includes every model."""
    all_models = list(Tortoise.apps.get_models_iterable())
    sorted_models = _topological_sort_models(all_models)
    assert set(sorted_models) == set(all_models)


@pytest.mark.asyncio
async def test_topological_sort_multi_level_chain(db):
    """MinRelation→Tournament and MinRelation→Team: MinRelation before both parents."""
    sorted_models = _topological_sort_models([Tournament, Team, MinRelation])
    assert sorted_models.index(MinRelation) < sorted_models.index(Tournament)
    assert sorted_models.index(MinRelation) < sorted_models.index(Team)


@pytest.mark.asyncio
async def test_topological_sort_multiple_fks_on_one_model(db):
    """Event has FKs to both Tournament and Reporter — must come before both."""
    sorted_models = _topological_sort_models([Tournament, Reporter, Event])
    assert sorted_models.index(Event) < sorted_models.index(Tournament)
    assert sorted_models.index(Event) < sorted_models.index(Reporter)


# ---------------------------------------------------------------------------
# truncate_all_models — integration tests against real DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_truncate_empty_db(db):
    """Truncating when tables are empty should succeed without error."""
    await truncate_all_models()


@pytest.mark.asyncio
async def test_truncate_clears_data(db):
    """Data created before truncation is gone after truncation."""
    tournament = await Tournament.create(name="Test Tournament")
    await Event.create(name="Test Event", tournament=tournament)

    await truncate_all_models()

    assert await Tournament.all().count() == 0
    assert await Event.all().count() == 0


@pytest.mark.asyncio
async def test_truncate_with_fk_constraints(db):
    """Truncation succeeds even with FK constraints (child→parent)."""
    t = await Tournament.create(name="T1")
    await Event.create(name="E1", tournament=t)
    await Event.create(name="E2", tournament=t)

    # This would fail with arbitrary order on strict FK enforcement
    await truncate_all_models()

    assert await Event.all().count() == 0
    assert await Tournament.all().count() == 0


@pytest.mark.asyncio
async def test_truncate_with_self_referential_fk(db):
    """Self-referential FK (Employee→Employee) doesn't break truncation."""
    boss = await Employee.create(name="Boss")
    await Employee.create(name="Worker", manager=boss)

    await truncate_all_models()

    assert await Employee.all().count() == 0


@pytest.mark.asyncio
async def test_truncate_raises_when_apps_not_loaded(db_simple):
    """truncate_all_models raises ValueError when apps aren't loaded."""
    from tortoise.context import get_current_context

    ctx = get_current_context()
    saved_apps = ctx._apps
    ctx._apps = {}
    try:
        with pytest.raises(ValueError, match="apps are not loaded"):
            await truncate_all_models()
    finally:
        ctx._apps = saved_apps
