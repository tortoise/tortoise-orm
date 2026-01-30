import pytest

from tests.testmodels import Tournament
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_explain(db):
    """Test that explain() returns query plan information.

    NOTE: we do not provide any guarantee on the format of the value
    returned by `.explain()`, as it heavily depends on the database.
    This test merely checks that one is able to run `.explain()`
    without errors for each backend.
    """
    plan = await Tournament.all().explain()
    # This should have returned *some* information.
    assert len(str(plan)) > 20
