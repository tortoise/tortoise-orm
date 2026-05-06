import pytest

from tests.testmodels import Tournament
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ, NotIn
from tortoise.exceptions import UnSupportedError


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


@requireCapability(dialect=NotIn("postgres", "mysql", "mssql"))
@pytest.mark.asyncio
async def test_explain_unsupported_output_fmt(db):
    await Tournament.create(name="Test")
    with pytest.raises(UnSupportedError, match="does not support different explain formats"):
        await Tournament.all().explain(output_fmt="json")


@requireCapability(dialect=NotIn("postgres", "mysql", "mssql"))
@pytest.mark.asyncio
async def test_explain_unsupported_options(db):
    await Tournament.create(name="Test")
    with pytest.raises(UnSupportedError, match="does not support explain options"):
        await Tournament.all().explain(analyze=True)
