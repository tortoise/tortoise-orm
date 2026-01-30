from unittest.mock import AsyncMock, Mock, PropertyMock, call, patch

import pytest

from tortoise import BaseDBAsyncClient, ConfigurationError
from tortoise.connection import ConnectionHandler


@pytest.fixture
def conn_handler():
    return ConnectionHandler()


def test_init_constructor(conn_handler):
    assert conn_handler._db_config is None
    assert conn_handler._create_db is False
    assert conn_handler._storage == {}


@pytest.mark.asyncio
@patch("tortoise.connection.ConnectionHandler._init_connections")
async def test_init(mocked_init_connections, conn_handler):
    db_config = {"default": {"HOST": "some_host", "PORT": "1234"}}
    await conn_handler._init(db_config, True)
    mocked_init_connections.assert_awaited_once()
    assert db_config == conn_handler._db_config
    assert conn_handler._create_db is True


def test_db_config_present(conn_handler):
    conn_handler._db_config = {"default": {"HOST": "some_host", "PORT": "1234"}}
    assert conn_handler.db_config == conn_handler._db_config


def test_db_config_not_present(conn_handler):
    err_msg = (
        "DB configuration not initialised. Make sure to call "
        "Tortoise.init with a valid configuration before attempting "
        "to create connections."
    )
    with pytest.raises(ConfigurationError, match=err_msg):
        _ = conn_handler.db_config


def test_get_storage(conn_handler):
    expected_ret_val = {"default": BaseDBAsyncClient("default")}
    conn_handler._storage = expected_ret_val
    ret_val = conn_handler._get_storage()
    assert ret_val == expected_ret_val
    assert ret_val is conn_handler._storage


def test_set_storage(conn_handler):
    new_storage = {"default": BaseDBAsyncClient("default")}
    conn_handler._set_storage(new_storage)
    assert conn_handler._storage == new_storage
    assert conn_handler._storage is new_storage


def test_copy_storage(conn_handler):
    original_storage = {"default": BaseDBAsyncClient("default")}
    conn_handler._storage = original_storage
    ret_val = conn_handler._copy_storage()
    assert ret_val == original_storage
    assert ret_val is not original_storage


def test_clear_storage(conn_handler):
    conn_handler._storage = {"default": BaseDBAsyncClient("default")}
    conn_handler._clear_storage()
    assert conn_handler._storage == {}


@patch("tortoise.connection.importlib.import_module")
def test_discover_client_class_proper_impl(mocked_import_module, conn_handler):
    mocked_import_module.return_value = Mock(client_class="some_class")
    del mocked_import_module.return_value.get_client_class
    client_class = conn_handler._discover_client_class({"engine": "blah"})

    mocked_import_module.assert_called_once_with("blah")
    assert client_class == "some_class"


@patch("tortoise.connection.importlib.import_module")
def test_discover_client_class_improper_impl(mocked_import_module, conn_handler):
    del mocked_import_module.return_value.client_class
    del mocked_import_module.return_value.get_client_class
    engine = "some_engine"
    with pytest.raises(
        ConfigurationError, match=f'Backend for engine "{engine}" does not implement db client'
    ):
        _ = conn_handler._discover_client_class({"engine": engine})


@patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
def test_get_db_info_present(mocked_db_config, conn_handler):
    expected_ret_val = {"HOST": "some_host", "PORT": "1234"}
    mocked_db_config.return_value = {"default": expected_ret_val}
    ret_val = conn_handler._get_db_info("default")
    assert ret_val == expected_ret_val


@patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
def test_get_db_info_not_present(mocked_db_config, conn_handler):
    mocked_db_config.return_value = {"default": {"HOST": "some_host", "PORT": "1234"}}
    conn_alias = "blah"
    with pytest.raises(
        ConfigurationError,
        match=f"Unable to get db settings for alias '{conn_alias}'",
    ):
        _ = conn_handler._get_db_info(conn_alias)


@pytest.mark.asyncio
@patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
@patch("tortoise.connection.ConnectionHandler.get")
async def test_init_connections_no_db_create(mocked_get, mocked_db_config, conn_handler):
    conn_1, conn_2 = AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)
    mocked_get.side_effect = [conn_1, conn_2]
    mocked_db_config.return_value = {
        "default": {"HOST": "some_host", "PORT": "1234"},
        "other": {"HOST": "some_other_host", "PORT": "1234"},
    }
    await conn_handler._init_connections()
    mocked_db_config.assert_called_once()
    mocked_get.assert_has_calls([call("default"), call("other")], any_order=True)
    conn_1.db_create.assert_not_awaited()
    conn_2.db_create.assert_not_awaited()


@pytest.mark.asyncio
@patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
@patch("tortoise.connection.ConnectionHandler.get")
async def test_init_connections_db_create(mocked_get, mocked_db_config, conn_handler):
    conn_handler._create_db = True
    conn_1, conn_2 = AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)
    mocked_get.side_effect = [conn_1, conn_2]
    mocked_db_config.return_value = {
        "default": {"HOST": "some_host", "PORT": "1234"},
        "other": {"HOST": "some_other_host", "PORT": "1234"},
    }
    await conn_handler._init_connections()
    mocked_db_config.assert_called_once()
    mocked_get.assert_has_calls([call("default"), call("other")], any_order=True)
    conn_1.db_create.assert_awaited_once()
    conn_2.db_create.assert_awaited_once()


@patch("tortoise.connection.ConnectionHandler._get_db_info")
@patch("tortoise.connection.expand_db_url")
@patch("tortoise.connection.ConnectionHandler._discover_client_class")
def test_create_connection_db_info_str(
    mocked_discover_client_class,
    mocked_expand_db_url,
    mocked_get_db_info,
    conn_handler,
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

    ret_val = conn_handler._create_connection(alias)

    mocked_get_db_info.assert_called_once_with(alias)
    mocked_expand_db_url.assert_called_once_with("some_db_url")
    mocked_discover_client_class.assert_called_once_with(
        {"engine": "some_engine", "credentials": {"cred_key": "some_val"}}
    )
    expected_client_class.assert_called_once_with(**expected_db_params)
    assert ret_val == "some_connection"


@patch("tortoise.connection.ConnectionHandler._get_db_info")
@patch("tortoise.connection.expand_db_url")
@patch("tortoise.connection.ConnectionHandler._discover_client_class")
def test_create_connection_db_info_not_str(
    mocked_discover_client_class,
    mocked_expand_db_url,
    mocked_get_db_info,
    conn_handler,
):
    alias = "default"
    mocked_get_db_info.return_value = {
        "engine": "some_engine",
        "credentials": {"cred_key": "some_val"},
    }
    expected_client_class = Mock(return_value="some_connection")
    mocked_discover_client_class.return_value = expected_client_class
    expected_db_params = {"cred_key": "some_val", "connection_name": alias}

    ret_val = conn_handler._create_connection(alias)

    mocked_get_db_info.assert_called_once_with(alias)
    mocked_expand_db_url.assert_not_called()
    mocked_discover_client_class.assert_called_once_with(
        {"engine": "some_engine", "credentials": {"cred_key": "some_val"}}
    )
    expected_client_class.assert_called_once_with(**expected_db_params)
    assert ret_val == "some_connection"


def test_get_alias_present(conn_handler):
    conn_handler._storage = {"default": "some_connection"}
    ret_val = conn_handler.get("default")
    assert ret_val == "some_connection"


@patch("tortoise.connection.ConnectionHandler._create_connection")
def test_get_alias_not_present(mocked_create_connection, conn_handler):
    conn_handler._storage = {"default": "some_connection"}
    mocked_create_connection.return_value = "some_other_connection"
    ret_val = conn_handler.get("other")
    mocked_create_connection.assert_called_once_with("other")
    assert ret_val == "some_other_connection"
    assert conn_handler._storage == {"default": "some_connection", "other": "some_other_connection"}


def test_set(conn_handler):
    conn_handler._storage = {"default": "existing_conn"}
    token = conn_handler.set("other", "some_conn")
    assert conn_handler._storage == {"default": "existing_conn", "other": "some_conn"}
    assert token is not None


def test_discard(conn_handler):
    conn_handler._storage = {"default": "some_conn", "other": "other_conn"}
    ret_val = conn_handler.discard("default")
    assert ret_val == "some_conn"
    assert conn_handler._storage == {"other": "other_conn"}


def test_reset(conn_handler):
    conn_handler._storage = {"default": "modified_conn", "other": "other_conn"}
    original_conn = Mock()
    token = Mock(_handler=conn_handler, _alias="default", _old_value=original_conn, _used=False)
    conn_handler.reset(token)
    assert conn_handler._storage["default"] is original_conn
    assert token._used is True


@patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
def test_all(mocked_db_config, conn_handler):
    conn_handler._storage = {"default": "some_conn", "other": "some_other_conn"}
    mocked_db_config.return_value = {"default": {}, "other": {}}
    ret_val = conn_handler.all()
    assert set(ret_val) == {"some_conn", "some_other_conn"}


@pytest.mark.asyncio
@patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
async def test_close_all_with_discard(mocked_db_config, conn_handler):
    conn_1, conn_2 = AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)
    conn_handler._storage = {"default": conn_1, "other": conn_2}
    conn_handler._db_config = {
        "default": {},
        "other": {},
    }  # Set _db_config so close_all doesn't early-return
    mocked_db_config.return_value = {"default": {}, "other": {}}
    await conn_handler.close_all()
    conn_1.close.assert_awaited_once()
    conn_2.close.assert_awaited_once()
    assert conn_handler._storage == {}


@pytest.mark.asyncio
@patch("tortoise.connection.ConnectionHandler.db_config", new_callable=PropertyMock)
async def test_close_all_without_discard(mocked_db_config, conn_handler):
    conn_1, conn_2 = AsyncMock(spec=BaseDBAsyncClient), AsyncMock(spec=BaseDBAsyncClient)
    conn_handler._storage = {"default": conn_1, "other": conn_2}
    conn_handler._db_config = {
        "default": {},
        "other": {},
    }  # Set _db_config so close_all doesn't early-return
    mocked_db_config.return_value = {"default": {}, "other": {}}
    await conn_handler.close_all(discard=False)
    conn_1.close.assert_awaited_once()
    conn_2.close.assert_awaited_once()
    assert conn_handler._storage == {"default": conn_1, "other": conn_2}
