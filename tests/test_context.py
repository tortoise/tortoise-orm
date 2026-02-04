"""
Tests for tortoise.context module - TortoiseContext class.

These tests verify the context-based state management for Tortoise ORM.

Note: These tests may run with a session-scoped default context active
(created by Tortoise.init() in conftest.py). The tests account for this
by testing context isolation relative to the current state.
"""

import pytest

from tortoise.connection import ConnectionHandler
from tortoise.context import (
    TortoiseContext,
    get_current_context,
    require_context,
    tortoise_test_context,
)
from tortoise.exceptions import ConfigurationError


class TestTortoiseContextInstantiation:
    """Test cases for TortoiseContext instantiation."""

    def test_context_instantiation_initial_state(self):
        """TortoiseContext instantiation has correct initial state."""
        ctx = TortoiseContext()

        assert ctx._connections is None
        assert ctx._apps is None
        assert ctx._inited is False
        assert ctx.inited is False

    def test_context_connections_property_lazy_creation(self):
        """ConnectionHandler is lazily created on first access."""
        ctx = TortoiseContext()

        # Before access
        assert ctx._connections is None

        # After access
        connections = ctx.connections
        assert ctx._connections is not None
        assert isinstance(connections, ConnectionHandler)

    def test_context_apps_property_initially_none(self):
        """Apps property is initially None."""
        ctx = TortoiseContext()

        assert ctx.apps is None


class TestContextManagerProtocol:
    """Test cases for context manager protocol."""

    def test_context_manager_sets_current_context(self):
        """Context manager sets current context."""
        # Save original context (may be session-scoped default)
        original_ctx = get_current_context()

        with TortoiseContext() as ctx:
            assert get_current_context() is ctx

        # After exit, should return to original
        assert get_current_context() is original_ctx

    def test_context_manager_resets_on_exit(self):
        """Context manager resets on exit."""
        original_ctx = get_current_context()

        with TortoiseContext():
            pass

        assert get_current_context() is original_ctx

    def test_nested_contexts_work_correctly(self):
        """Nested contexts work correctly."""
        original_ctx = get_current_context()

        with TortoiseContext() as outer:
            assert get_current_context() is outer

            with TortoiseContext() as inner:
                assert get_current_context() is inner

            # After inner exits, should return to outer
            assert get_current_context() is outer

        # After all exit, should return to original
        assert get_current_context() is original_ctx


class TestRequireContext:
    """Test cases for require_context function."""

    def test_require_context_raises_when_no_context(self):
        """require_context raises when no context is active.

        Note: With the new architecture, Tortoise.init() creates a default context,
        so this test only passes when run in complete isolation. When a session-scoped
        context exists, require_context() returns it instead of raising.
        """
        # This behavior depends on whether a session context exists
        original_ctx = get_current_context()
        if original_ctx is not None:
            # Session context exists, require_context should return it
            result = require_context()
            assert result is original_ctx
        else:
            # No session context, should raise
            with pytest.raises(RuntimeError) as exc_info:
                require_context()
            assert "No TortoiseContext is currently active" in str(exc_info.value)

    def test_require_context_returns_active_context(self):
        """require_context returns the active context when one exists."""
        with TortoiseContext() as ctx:
            result = require_context()
            assert result is ctx


class TestConnectionHandlerIsolation:
    """Test cases for ConnectionHandler isolation."""

    def test_each_context_gets_own_connection_handler(self):
        """Each context gets own ConnectionHandler."""
        ctx1 = TortoiseContext()
        ctx2 = TortoiseContext()

        # Access connections property on both
        conn1 = ctx1.connections
        conn2 = ctx2.connections

        # Should be different instances
        assert conn1 is not conn2

    def test_context_connections_isolated_from_global(self):
        """Context connections isolated from global."""
        ctx = TortoiseContext()

        # Context's ConnectionHandler should be completely independent
        # It should not have any config yet
        with pytest.raises(ConfigurationError):
            ctx.connections.db_config


class TestAsyncContextManager:
    """Test cases for async context manager protocol."""

    @pytest.mark.asyncio
    async def test_async_context_manager_sets_current_context(self):
        """Async context manager sets current context."""
        original_ctx = get_current_context()

        async with TortoiseContext() as ctx:
            assert get_current_context() is ctx

        # After exit, should return to original
        assert get_current_context() is original_ctx

    @pytest.mark.asyncio
    async def test_async_context_manager_resets_on_exit(self):
        """Async context manager resets on exit."""
        original_ctx = get_current_context()

        async with TortoiseContext():
            pass

        assert get_current_context() is original_ctx

    @pytest.mark.asyncio
    async def test_connections_cleaned_on_async_context_exit(self):
        """Connections closed on async context exit."""
        ctx = TortoiseContext()

        # Access connections to create the handler
        _ = ctx.connections
        assert ctx._connections is not None

        async with ctx:
            pass

        # After exit, connections should be cleaned up
        assert ctx._connections is None

    @pytest.mark.asyncio
    async def test_apps_cleared_on_async_context_exit(self):
        """Apps cleared on context exit."""
        ctx = TortoiseContext()

        async with ctx:
            # Manually set apps to simulate initialization
            ctx._apps = {}
            ctx._inited = True

        # After exit, apps should be cleared
        assert ctx.apps is None
        assert ctx.inited is False


class TestGetModel:
    """Test cases for get_model method."""

    def test_get_model_raises_when_not_initialized(self):
        """get_model raises when not initialized."""
        ctx = TortoiseContext()

        with pytest.raises(ConfigurationError) as exc_info:
            ctx.get_model("models", "User")

        assert "Context not initialized" in str(exc_info.value)


class TestInit:
    """Test cases for init method."""

    @pytest.mark.asyncio
    async def test_init_raises_without_required_params(self):
        """init() raises without required params."""
        ctx = TortoiseContext()

        with pytest.raises(ConfigurationError) as exc_info:
            await ctx.init()

        assert "Must provide either 'config', 'config_file', or both 'db_url' and 'modules'" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_init_raises_with_only_db_url(self):
        """init() raises with only db_url (no modules)."""
        ctx = TortoiseContext()

        with pytest.raises(ConfigurationError) as exc_info:
            await ctx.init(db_url="sqlite://:memory:")

        assert "Must provide either 'config', 'config_file', or both 'db_url' and 'modules'" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_init_raises_with_only_modules(self):
        """init() raises with only modules (no db_url)."""
        ctx = TortoiseContext()

        with pytest.raises(ConfigurationError) as exc_info:
            await ctx.init(modules={"models": ["tests.testmodels"]})

        assert "Must provide either 'config', 'config_file', or both 'db_url' and 'modules'" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_init_raises_with_invalid_config_no_connections(self):
        """init() raises when config missing connections section."""
        ctx = TortoiseContext()

        with pytest.raises(ConfigurationError) as exc_info:
            await ctx.init(config={"apps": {}})

        assert 'Config must define "connections" section' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_init_raises_with_invalid_config_no_apps(self):
        """init() raises when config missing apps section."""
        ctx = TortoiseContext()

        with pytest.raises(ConfigurationError) as exc_info:
            await ctx.init(config={"connections": {}})

        assert 'Config must define "apps" section' in str(exc_info.value)


class TestGenerateSchemas:
    """Test cases for generate_schemas method."""

    @pytest.mark.asyncio
    async def test_generate_schemas_raises_when_not_initialized(self):
        """generate_schemas() raises when context not initialized."""
        ctx = TortoiseContext()

        with pytest.raises(ConfigurationError) as exc_info:
            await ctx.generate_schemas()

        assert "Context not initialized" in str(exc_info.value)


class TestTortoiseTestContext:
    """Test cases for tortoise_test_context helper."""

    @pytest.mark.asyncio
    async def test_tortoise_test_context_creates_isolated_context(self):
        """tortoise_test_context creates isolated context."""
        original_ctx = get_current_context()

        async with tortoise_test_context(["tests.testmodels"]) as ctx:
            # Context should be active
            assert get_current_context() is ctx
            # Context should be initialized
            assert ctx.inited is True
            # Context should have apps
            assert ctx.apps is not None

        # Context should be restored to original (session context if present)
        assert get_current_context() is original_ctx

    @pytest.mark.asyncio
    async def test_tortoise_test_context_multiple_isolated(self):
        """Multiple tortoise_test_context calls are isolated."""
        async with tortoise_test_context(["tests.testmodels"]) as ctx1:
            conn1 = ctx1.connections

        async with tortoise_test_context(["tests.testmodels"]) as ctx2:
            conn2 = ctx2.connections

        # Different context instances
        assert ctx1 is not ctx2
        # Different connection handlers
        assert conn1 is not conn2


class TestInitIntegration:
    """Integration test cases for init method."""

    @pytest.mark.asyncio
    async def test_init_with_db_url_and_modules(self):
        """init() with db_url and modules initializes context correctly."""
        async with TortoiseContext() as ctx:
            await ctx.init(
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
            )

            # Context should be initialized
            assert ctx.inited is True

            # Connections should be populated
            assert ctx._connections is not None
            # Should be able to get the default connection
            conn = ctx.connections.get("default")
            assert conn is not None

            # Apps should be populated
            assert ctx.apps is not None
            # Should be able to get a model
            Author = ctx.get_model("models", "Author")
            assert Author.__name__ == "Author"

    @pytest.mark.asyncio
    async def test_generate_schemas_creates_tables(self):
        """generate_schemas() creates tables in the database."""
        async with TortoiseContext() as ctx:
            await ctx.init(
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
            )
            await ctx.generate_schemas()

            # Verify tables exist by querying sqlite_master
            conn = ctx.connections.get("default")
            result = await conn.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='author'"
            )
            tables = [row["name"] for row in result[1]]
            assert "author" in tables

    @pytest.mark.asyncio
    async def test_full_context_lifecycle_with_crud(self):
        """Full context lifecycle with model CRUD operations."""
        original_ctx = get_current_context()

        async with TortoiseContext() as ctx:
            await ctx.init(
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
            )
            await ctx.generate_schemas()

            # Import model inside test to ensure it uses active context
            from tests.testmodels import Author

            # CREATE
            author = await Author.create(name="Test Author")
            assert author.id is not None
            assert author.name == "Test Author"

            # READ
            fetched = await Author.get(id=author.id)
            assert fetched.name == "Test Author"

            # UPDATE
            fetched.name = "Updated Author"
            await fetched.save()
            updated = await Author.get(id=author.id)
            assert updated.name == "Updated Author"

            # DELETE
            await updated.delete()
            count = await Author.filter(id=author.id).count()
            assert count == 0

        # Context should be restored to original (session context if present)
        assert get_current_context() is original_ctx


class TestModelContextResolution:
    """Test cases for model context resolution."""

    @pytest.mark.asyncio
    async def test_model_uses_context_connections_when_active(self):
        """Model uses context when context is active."""
        async with TortoiseContext() as ctx:
            await ctx.init(
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
            )
            await ctx.generate_schemas()

            from tests.testmodels import Author

            # Create a record
            author = await Author.create(name="Context Author")
            assert author.id is not None

            # Verify we can query it
            all_authors = await Author.all()
            assert len(all_authors) == 1
            assert all_authors[0].name == "Context Author"

    @pytest.mark.asyncio
    async def test_sequential_contexts_isolated(self):
        """Sequential contexts are isolated from each other."""
        from tests.testmodels import Author

        # First context creates its own author
        async with TortoiseContext() as ctx1:
            await ctx1.init(
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
            )
            await ctx1.generate_schemas()

            await Author.create(name="Author in Context 1")
            authors_in_ctx1 = await Author.all()
            assert len(authors_in_ctx1) == 1
            assert authors_in_ctx1[0].name == "Author in Context 1"

        # Second context should start with empty database
        async with TortoiseContext() as ctx2:
            await ctx2.init(
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
            )
            await ctx2.generate_schemas()

            # Should be empty - isolated from first context
            authors_before = await Author.all()
            assert len(authors_before) == 0, "Second context should start empty"

            await Author.create(name="Author in Context 2")
            authors_in_ctx2 = await Author.all()
            assert len(authors_in_ctx2) == 1
            assert authors_in_ctx2[0].name == "Author in Context 2"


class TestTimezoneAndRouters:
    """Test cases for timezone and routers configuration."""

    def test_context_default_timezone_settings(self):
        """Context has default timezone settings."""
        ctx = TortoiseContext()
        assert ctx.use_tz is False
        assert ctx.timezone == "UTC"
        assert ctx.routers == []

    @pytest.mark.asyncio
    async def test_init_with_timezone_settings(self):
        """Context can be initialized with timezone settings."""
        async with TortoiseContext() as ctx:
            await ctx.init(
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
                use_tz=True,
                timezone="America/New_York",
            )

            assert ctx.use_tz is True
            assert ctx.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_init_with_config_dict_timezone(self):
        """Timezone settings from config dict are used."""
        async with TortoiseContext() as ctx:
            await ctx.init(
                config={
                    "connections": {"default": "sqlite://:memory:"},
                    "apps": {"models": {"models": ["tests.testmodels"]}},
                    "use_tz": True,
                    "timezone": "Europe/London",
                }
            )

            assert ctx.use_tz is True
            assert ctx.timezone == "Europe/London"

    @pytest.mark.asyncio
    async def test_tortoise_test_context_with_timezone(self):
        """tortoise_test_context supports timezone parameters."""
        async with tortoise_test_context(
            ["tests.testmodels"],
            use_tz=True,
            timezone="Asia/Tokyo",
        ) as ctx:
            assert ctx.use_tz is True
            assert ctx.timezone == "Asia/Tokyo"


class TestTortoiseConfigValidation:
    """Test cases for TortoiseConfig validation in ctx.init()."""

    @pytest.mark.asyncio
    async def test_init_accepts_tortoise_config_object(self):
        """ctx.init() accepts TortoiseConfig object directly."""
        from tortoise.config import AppConfig, DBUrlConfig, TortoiseConfig

        config = TortoiseConfig(
            connections={"default": DBUrlConfig("sqlite://:memory:")},
            apps={"models": AppConfig(models=["tests.testmodels"])},
            use_tz=True,
            timezone="UTC",
        )

        async with TortoiseContext() as ctx:
            await ctx.init(config=config)
            assert ctx.inited is True
            assert ctx.use_tz is True

    @pytest.mark.asyncio
    async def test_init_validates_dict_config(self):
        """ctx.init() validates dict config and raises ConfigurationError on issues."""
        async with TortoiseContext() as ctx:
            # Config with missing 'models' in app should raise ConfigurationError
            # because TortoiseConfig.from_dict validates the structure
            with pytest.raises(ConfigurationError) as exc_info:
                await ctx.init(
                    config={
                        "connections": {"default": "sqlite://:memory:"},
                        "apps": {"models": {}},  # Missing 'models' key
                    }
                )
            assert "models" in str(exc_info.value).lower()
