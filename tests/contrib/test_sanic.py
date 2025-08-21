"""
Test Sanic contrib integration
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tortoise.contrib.sanic import register_tortoise


class TestSanicIntegration(unittest.TestCase):
    """Test Sanic Tortoise integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = MagicMock()
        self.app.ctx = MagicMock()
        self.app.before_server_start = MagicMock()
        self.app.after_server_stop = MagicMock()
        self.app.middleware = MagicMock()

    def test_register_tortoise_basic(self):
        """Test basic registration"""
        register_tortoise(
            self.app,
            db_url="sqlite://:memory:",
            modules={"models": ["tests.testmodels"]},
        )
        
        # Check that listeners were registered
        self.app.before_server_start.assert_called_once()
        self.app.after_server_stop.assert_called_once()

    def test_register_tortoise_with_config(self):
        """Test registration with config dict"""
        config = {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": ":memory:"},
                }
            },
            "apps": {
                "models": {
                    "models": ["tests.testmodels"],
                    "default_connection": "default",
                }
            },
        }
        
        register_tortoise(self.app, config=config)
        
        # Check that listeners were registered
        self.app.before_server_start.assert_called_once()
        self.app.after_server_stop.assert_called_once()

    def test_register_tortoise_config_file(self):
        """Test registration with config file"""
        with patch("tortoise.contrib.sanic.generate_config_from_file") as mock_gen:
            mock_gen.return_value = {
                "connections": {"default": {}},
                "apps": {"models": {}},
            }
            
            register_tortoise(self.app, config_file="config.json")
            
            mock_gen.assert_called_once_with("config.json")
            self.app.before_server_start.assert_called_once()
            self.app.after_server_stop.assert_called_once()

    def test_register_tortoise_with_generate_schemas(self):
        """Test registration with generate_schemas=True"""
        register_tortoise(
            self.app,
            db_url="sqlite://:memory:",
            modules={"models": ["tests.testmodels"]},
            generate_schemas=True,
        )
        
        # Verify the before_server_start handler was registered
        self.app.before_server_start.assert_called_once()

    def test_register_tortoise_session_management(self):
        """Test session management middleware registration"""
        register_tortoise(
            self.app,
            db_url="sqlite://:memory:",
            modules={"models": ["tests.testmodels"]},
            session_management=True,
        )
        
        # Check that middleware was registered
        self.app.middleware.assert_called_once_with("request")

    @patch("tortoise.contrib.sanic.Tortoise")
    async def test_init_orm_handler(self, mock_tortoise):
        """Test the init_orm handler"""
        mock_tortoise.init = AsyncMock()
        
        # Register and get the handler
        register_tortoise(
            self.app,
            db_url="sqlite://:memory:",
            modules={"models": ["tests.testmodels"]},
        )
        
        # Get the registered handler
        handler = self.app.before_server_start.call_args[0][0]
        
        # Call the handler
        await handler(self.app)
        
        # Verify Tortoise.init was called
        mock_tortoise.init.assert_called_once()

    @patch("tortoise.contrib.sanic.Tortoise")
    async def test_close_orm_handler(self, mock_tortoise):
        """Test the close_orm handler"""
        mock_tortoise.close_connections = AsyncMock()
        
        # Register and get the handler
        register_tortoise(
            self.app,
            db_url="sqlite://:memory:",
            modules={"models": ["tests.testmodels"]},
        )
        
        # Get the registered handler
        handler = self.app.after_server_stop.call_args[0][0]
        
        # Call the handler
        await handler(self.app)
        
        # Verify Tortoise.close_connections was called
        mock_tortoise.close_connections.assert_called_once()

    @patch("tortoise.contrib.sanic.connections")
    async def test_session_middleware(self, mock_connections):
        """Test session management middleware"""
        # Mock connection
        mock_conn = AsyncMock()
        mock_conn.in_transaction = MagicMock()
        mock_connections.get.return_value = mock_conn
        
        # Mock transaction context
        mock_trans = AsyncMock()
        mock_trans.__aenter__ = AsyncMock(return_value=mock_trans)
        mock_trans.__aexit__ = AsyncMock(return_value=None)
        mock_conn.in_transaction.return_value = mock_trans
        
        # Register with session management
        register_tortoise(
            self.app,
            db_url="sqlite://:memory:",
            modules={"models": ["tests.testmodels"]},
            session_management=True,
        )
        
        # Get the middleware
        middleware_decorator = self.app.middleware.call_args[0][0]
        middleware_func = self.app.middleware.return_value.call_args[0][0]
        
        # Create mock request
        request = MagicMock()
        request.ctx = MagicMock()
        
        # Call middleware
        await middleware_func(request)
        
        # Verify transaction was created
        mock_conn.in_transaction.assert_called_once()
        mock_trans.__aenter__.assert_called_once()

    def test_invalid_config_params(self):
        """Test that invalid config parameters raise errors"""
        with self.assertRaises(ValueError):
            register_tortoise(self.app)  # No config provided
            
        with self.assertRaises(ValueError):
            register_tortoise(
                self.app,
                db_url="sqlite://:memory:",
                config={"connections": {}},  # Both db_url and config
            )

    def test_app_context_storage(self):
        """Test that config is stored in app context"""
        config = {
            "connections": {"default": {}},
            "apps": {"models": {}},
        }
        
        register_tortoise(self.app, config=config)
        
        # Verify config was stored in app context
        self.assertEqual(self.app.ctx.tortoise_config, config)

    async def test_generate_schemas_handler(self):
        """Test generate_schemas in init handler"""
        with patch("tortoise.contrib.sanic.Tortoise") as mock_tortoise:
            mock_tortoise.init = AsyncMock()
            mock_tortoise.generate_schemas = AsyncMock()
            
            # Register with generate_schemas=True
            register_tortoise(
                self.app,
                db_url="sqlite://:memory:",
                modules={"models": ["tests.testmodels"]},
                generate_schemas=True,
            )
            
            # Get and call the handler
            handler = self.app.before_server_start.call_args[0][0]
            await handler(self.app)
            
            # Verify generate_schemas was called
            mock_tortoise.generate_schemas.assert_called_once()

    def test_custom_app_name(self):
        """Test custom app name in modules"""
        register_tortoise(
            self.app,
            db_url="sqlite://:memory:",
            modules={"myapp": ["myapp.models"]},
        )
        
        # Check config was created with custom app name
        expected_config = {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": ":memory:"},
                }
            },
            "apps": {
                "myapp": {
                    "models": ["myapp.models"],
                    "default_connection": "default",
                }
            },
        }
        
        self.assertEqual(self.app.ctx.tortoise_config, expected_config)