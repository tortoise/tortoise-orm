import pytest

from tortoise import connections
from tortoise.contrib.test import requireCapability
from tortoise.exceptions import ConfigurationError


@pytest.fixture
def db_and_caps(db):
    """Get database connection and capabilities."""
    db_conn = connections.get("models")
    return db_conn, db_conn.capabilities


@pytest.mark.asyncio
async def test_str(db):
    """Test capabilities string representation."""
    caps = connections.get("models").capabilities
    assert "requires_limit" in str(caps)


@pytest.mark.asyncio
async def test_immutability_1(db):
    """Test capabilities are immutable."""
    caps = connections.get("models").capabilities
    assert isinstance(caps.dialect, str)
    with pytest.raises(AttributeError):
        caps.dialect = "foo"


@pytest.mark.xfail(raises=ConfigurationError, reason="Connection 'other' does not exist")
@requireCapability(connection_name="other")
@pytest.mark.asyncio
async def test_connection_name(db):
    """Will fail with a ConfigurationError since connection 'other' does not exist."""
    pass


@requireCapability(dialect="sqlite")
@pytest.mark.xfail(reason="Test is expected to fail - testing xfail behavior")
@pytest.mark.asyncio
async def test_actually_runs(db):
    """Test that xfail actually runs."""
    assert False


@pytest.mark.asyncio
async def test_attribute_error(db):
    """Test capabilities raise AttributeError on invalid attribute assignment."""
    caps = connections.get("models").capabilities
    with pytest.raises(AttributeError):
        caps.bar = "foo"


@requireCapability(dialect="sqlite")
@pytest.mark.asyncio
async def test_dialect_sqlite(db):
    """Test sqlite dialect capability."""
    caps = connections.get("models").capabilities
    assert caps.dialect == "sqlite"


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_dialect_mysql(db):
    """Test mysql dialect capability."""
    caps = connections.get("models").capabilities
    assert caps.dialect == "mysql"


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_dialect_postgres(db):
    """Test postgres dialect capability."""
    caps = connections.get("models").capabilities
    assert caps.dialect == "postgres"
