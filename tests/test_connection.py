from contextvars import ContextVar
from unittest.mock import AsyncMock, Mock, PropertyMock, call, patch

from tortoise import BaseDBAsyncClient, ConfigurationError
from tortoise.connection import ConnectionHandler
from tortoise.contrib.test import SimpleTestCase


class TestConnections(SimpleTestCase):
    def setUp(self) -> None:
        self.conn_handler = ConnectionHandler()

    def test_init_constructor(self):
        self.assertIsNone(self.conn_handler._db_config)
        self.assertFalse(self.conn_handler._create_db)

    @patch("tortoise.connection.ConnectionHandler._init_connections")
    async def test_init(self, mocked_init_connections: AsyncMock):
        db_config = {"default": {"HOST": "some_host", "PORT": "1234"}}
        await self.conn_handler._init(db_config, True)
        mocked_init_connections.assert_awaited_once()
        self.assertEqual(db_config, self.conn_handler._db_config)
        self.assertTrue(self.conn_handler._create_db)

    def test_db_config_present(self):
        self.conn_handler._db_config = {"default": {"HOST": "some_host", "PORT": "1234"}}
        self.assertEqual(self.conn_handler.db_config, self.conn_handler._db_config)

    def test_db_config_not_present(self):
        err_msg = (
            "DB configuration not initialised. Make sure to call "
            "Tortoise.init with a valid configuration before attempting "
            "to create connections."
        )
        with self.assertRaises(ConfigurationError, msg=err_msg):
            _ = self.conn_handler.db_config

    @patch("tortoise.connection.ConnectionHandler._conn_storage", spec=ContextVar)
    def test_get_storage(self, mocked_conn_storage: Mock):
        expected_ret_val = {"default": BaseDBAsyncClient("default")}
        mocked_conn_storage.get.return_value = expected_ret_val
        ret_val = self.conn_handler._get_storage()
        self.assertDictEqual(ret_val, expected_ret_val)

    @patch("tortoise.connection.ConnectionHandler._conn_storage", spec=ContextVar)
    def test_set_storage(self, mocked_conn_storage: Mock):
        mocked_conn_storage.set.return_value = "blah"
        new_storage = {"default": BaseDBAsyncClient("default")}
        ret_val = self.conn_handler._set_storage(new_storage)
        mocked_conn_storage.set.assert_called_once_with(new_storage)
        self.assertEqual(ret_val, mocked_conn_storage.set.return_value)

    @patch("tortoise.connection.ConnectionHandler._get_storage")
    @patch("tortoise.connection.copy")
    def test_copy_storage(self, mocked_copy: Mock, mocked_get_storage: Mock):
        expected_ret_value = {"default": BaseDBAsyncClient("default")}
        mocked_get_storage.return_value = expected_ret_value
        mocked_copy.return_value = expected_ret_value.copy()
        ret_val = self.conn_handler._copy_storage()
        mocked_get_storage.assert_called_once()
        mocked_copy.assert_called_once_with(mocked_get_storage.return_value)
        self.assertDictEqual(ret_val, expected_ret_value)
        self.assertNotEqual(id(expected_ret_value), id(ret_val))

    @patch("tortoise.connection.ConnectionHandler._get_storage")
    def test_clear_storage(self, mocked_get_storage: Mock):
        self.conn_handler._clear_storage()
        mocked_get_storage.assert_called_once()
        mocked_get_storage.return_value.clear.assert_called_once()

    @patch("tortoise.connection.importlib.import_module")
    def test_discover_client_class_proper_impl(self, mocked_import_module: Mock):
        mocked_import_module.return_value = Mock(client_class="some_class")
        del mocked_import_module.return_value.get_client_class
        client_class = self.conn_handler._discover_client_class({"engine": "blah"})

        mocked_import_module.assert_called_once_with("blah")
        self.assertEqual(client_class, "some_class")

    @patch("tortoise.connection.importlib.import_module")
    def test_discover_client_class_improper_impl(self, mocked_import_module: Mock):
        del mocked_import_module.return_value.client_class
        del mocked_import_module.return_value.get_client_class
        engine = "some_engine"
        with self.assertRaises(
            ConfigurationError, msg=f'Backend for engine "{engine}" does not implement db client'
        ):
            _ = self.conn_handler._discover_client_class({"engine": engine})

    @patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
    def test_get_db_info_present(self, mocked_db_config: Mock):
        expected_ret_val = {"HOST": "some_host", "PORT": "1234"}
        mocked_db_config.return_value = {"default": expected_ret_val}
        ret_val = self.conn_handler._get_db_info("default")
        self.assertEqual(ret_val, expected_ret_val)

    @patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
    def test_get_db_info_not_present(self, mocked_db_config: Mock):
        mocked_db_config.return_value = {"default": {"HOST": "some_host", "PORT": "1234"}}
        conn_alias = "blah"
        with self.assertRaises(
            ConfigurationError,
            msg=f"Unable to get db settings for alias '{conn_alias}'. Please "
            f"check if the config dict contains this alias and try again",
        ):
            _ = self.conn_handler._get_db_info(conn_alias)

    @patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
    @patch("tortoise.connection.ConnectionHandler.get")
    async def test_init_connections_no_db_create(self, mocked_get: Mock, mocked_db_config: Mock):
        conn_1, conn_2 = AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)
        mocked_get.side_effect = [conn_1, conn_2]
        mocked_db_config.return_value = {
            "default": {"HOST": "some_host", "PORT": "1234"},
            "other": {"HOST": "some_other_host", "PORT": "1234"},
        }
        await self.conn_handler._init_connections()
        mocked_db_config.assert_called_once()
        mocked_get.assert_has_calls([call("default"), call("other")], any_order=True)
        conn_1.db_create.assert_not_awaited()
        conn_2.db_create.assert_not_awaited()

    @patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
    @patch("tortoise.connection.ConnectionHandler.get")
    async def test_init_connections_db_create(self, mocked_get: Mock, mocked_db_config: Mock):
        self.conn_handler._create_db = True
        conn_1, conn_2 = AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)
        mocked_get.side_effect = [conn_1, conn_2]
        mocked_db_config.return_value = {
            "default": {"HOST": "some_host", "PORT": "1234"},
            "other": {"HOST": "some_other_host", "PORT": "1234"},
        }
        await self.conn_handler._init_connections()
        mocked_db_config.assert_called_once()
        mocked_get.assert_has_calls([call("default"), call("other")], any_order=True)
        conn_1.db_create.assert_awaited_once()
        conn_2.db_create.assert_awaited_once()

    @patch("tortoise.connection.ConnectionHandler._get_db_info")
    @patch("tortoise.connection.expand_db_url")
    @patch("tortoise.connection.ConnectionHandler._discover_client_class")
    def test_create_connection_db_info_str(
        self,
        mocked_discover_client_class: Mock,
        mocked_expand_db_url: Mock,
        mocked_get_db_info: Mock,
    ):
        alias = "default"
        mocked_get_db_info.return_value = "some_db_url"
        mocked_expand_db_url.return_value = {
            "engine": "some_engine",
            "credentials": {"cred_key": "some_val"},
        }
        expected_client_class = Mock(return_value="some_connection")
        mocked_discover_client_class.return_value = expected_client_class
        expected_db_params = {"cred_key": "some_val", "connection_name": alias}

        ret_val = self.conn_handler._create_connection(alias)

        mocked_get_db_info.assert_called_once_with(alias)
        mocked_expand_db_url.assert_called_once_with("some_db_url")
        mocked_discover_client_class.assert_called_once_with(
            {"engine": "some_engine", "credentials": {"cred_key": "some_val"}}
        )
        expected_client_class.assert_called_once_with(**expected_db_params)
        self.assertEqual(ret_val, "some_connection")

    @patch("tortoise.connection.ConnectionHandler._get_db_info")
    @patch("tortoise.connection.expand_db_url")
    @patch("tortoise.connection.ConnectionHandler._discover_client_class")
    def test_create_connection_db_info_not_str(
        self,
        mocked_discover_client_class: Mock,
        mocked_expand_db_url: Mock,
        mocked_get_db_info: Mock,
    ):
        alias = "default"
        mocked_get_db_info.return_value = {
            "engine": "some_engine",
            "credentials": {"cred_key": "some_val"},
        }
        expected_client_class = Mock(return_value="some_connection")
        mocked_discover_client_class.return_value = expected_client_class
        expected_db_params = {"cred_key": "some_val", "connection_name": alias}

        ret_val = self.conn_handler._create_connection(alias)

        mocked_get_db_info.assert_called_once_with(alias)
        mocked_expand_db_url.assert_not_called()
        mocked_discover_client_class.assert_called_once_with(
            {"engine": "some_engine", "credentials": {"cred_key": "some_val"}}
        )
        expected_client_class.assert_called_once_with(**expected_db_params)
        self.assertEqual(ret_val, "some_connection")

    @patch("tortoise.connection.ConnectionHandler._get_storage")
    @patch("tortoise.connection.ConnectionHandler._create_connection")
    def test_get_alias_present(self, mocked_create_connection: Mock, mocked_get_storage: Mock):
        mocked_get_storage.return_value = {"default": "some_connection"}
        ret_val = self.conn_handler.get("default")
        mocked_get_storage.assert_called_once()
        mocked_create_connection.assert_not_called()
        self.assertEqual(ret_val, "some_connection")

    @patch("tortoise.connection.ConnectionHandler._get_storage")
    @patch("tortoise.connection.ConnectionHandler._create_connection")
    def test_get_alias_not_present(self, mocked_create_connection: Mock, mocked_get_storage: Mock):
        mocked_get_storage.return_value = {"default": "some_connection"}
        expected_final_dict = {**mocked_get_storage.return_value, "other": "some_other_connection"}
        mocked_create_connection.return_value = "some_other_connection"
        ret_val = self.conn_handler.get("other")
        mocked_get_storage.assert_called_once()
        mocked_create_connection.assert_called_once_with("other")
        self.assertEqual(ret_val, "some_other_connection")
        self.assertDictEqual(mocked_get_storage.return_value, expected_final_dict)

    @patch("tortoise.connection.ConnectionHandler._conn_storage", spec=ContextVar)
    @patch("tortoise.connection.ConnectionHandler._copy_storage")
    def test_set(self, mocked_copy_storage: Mock, mocked_conn_storage: Mock):
        mocked_copy_storage.return_value = {}
        expected_storage = {"default": "some_conn"}
        mocked_conn_storage.set.return_value = "some_token"
        ret_val = self.conn_handler.set("default", "some_conn")  # type: ignore
        mocked_copy_storage.assert_called_once()
        self.assertEqual(ret_val, mocked_conn_storage.set.return_value)
        self.assertDictEqual(expected_storage, mocked_copy_storage.return_value)

    @patch("tortoise.connection.ConnectionHandler._get_storage")
    def test_discard(self, mocked_get_storage: Mock):
        mocked_get_storage.return_value = {"default": "some_conn"}
        ret_val = self.conn_handler.discard("default")
        self.assertEqual(ret_val, "some_conn")
        self.assertDictEqual({}, mocked_get_storage.return_value)

    @patch("tortoise.connection.ConnectionHandler._conn_storage", spec=ContextVar)
    @patch("tortoise.connection.ConnectionHandler._get_storage")
    def test_reset(self, mocked_get_storage: Mock, mocked_conn_storage: Mock):
        first_config = {"other": "some_other_conn", "default": "diff_conn"}
        second_config = {"default": "some_conn"}
        mocked_get_storage.side_effect = [first_config, second_config]
        final_storage = {"default": "some_conn", "other": "some_other_conn"}
        self.conn_handler.reset("some_token")  # type: ignore
        mocked_get_storage.assert_has_calls([call(), call()])
        mocked_conn_storage.reset.assert_called_once_with("some_token")
        self.assertDictEqual(final_storage, second_config)

    @patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
    @patch("tortoise.connection.ConnectionHandler.get")
    def test_all(self, mocked_get: Mock, mocked_db_config: Mock):
        db_config = {"default": "some_conn", "other": "some_other_conn"}

        def side_effect_callable(alias):
            return db_config[alias]

        mocked_get.side_effect = side_effect_callable
        mocked_db_config.return_value = db_config
        expected_result = ["some_conn", "some_other_conn"]
        ret_val = self.conn_handler.all()
        mocked_db_config.assert_called_once()
        mocked_get.assert_has_calls([call("default"), call("other")], any_order=True)
        self.assertEqual(ret_val, expected_result)

    @patch("tortoise.connection.ConnectionHandler.all")
    @patch("tortoise.connection.ConnectionHandler.discard")
    @patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
    async def test_close_all_with_discard(
        self, mocked_db_config: Mock, mocked_discard: Mock, mocked_all: Mock
    ):
        all_conn = [AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)]
        db_config = {"default": "some_config", "other": "some_other_config"}
        mocked_all.return_value = all_conn
        mocked_db_config.return_value = db_config
        await self.conn_handler.close_all()
        mocked_all.assert_called_once()
        mocked_db_config.assert_called_once()
        for mock_obj in all_conn:
            mock_obj.close.assert_awaited_once()
        mocked_discard.assert_has_calls([call("default"), call("other")], any_order=True)

    @patch("tortoise.connection.ConnectionHandler.all")
    async def test_close_all_without_discard(self, mocked_all: Mock):
        all_conn = [AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)]
        mocked_all.return_value = all_conn
        await self.conn_handler.close_all(discard=False)
        mocked_all.assert_called_once()
        for mock_obj in all_conn:
            mock_obj.close.assert_awaited_once()
