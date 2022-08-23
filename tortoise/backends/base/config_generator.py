import urllib.parse as urlparse
import uuid
from types import ModuleType
from typing import Any, Dict, Iterable, Optional, Union

from tortoise.exceptions import ConfigurationError

urlparse.uses_netloc.append("postgres")
urlparse.uses_netloc.append("asyncpg")
urlparse.uses_netloc.append("psycopg")
urlparse.uses_netloc.append("sqlite")
urlparse.uses_netloc.append("mysql")
urlparse.uses_netloc.append("oracle")
urlparse.uses_netloc.append("mssql")
DB_LOOKUP: Dict[str, Dict[str, Any]] = {
    "psycopg": {
        "engine": "tortoise.backends.psycopg",
        "vmap": {
            "path": "database",
            "hostname": "host",
            "port": "port",
            "username": "user",
            "password": "password",
        },
        "defaults": {"port": 5432},
        "cast": {
            "min_size": int,
            "max_size": int,
            "max_queries": int,
            "max_inactive_connection_lifetime": float,
            "timeout": int,
            "statement_cache_size": int,
            "max_cached_statement_lifetime": int,
            "max_cacheable_statement_size": int,
            "ssl": bool,
        },
    },
    "asyncpg": {
        "engine": "tortoise.backends.asyncpg",
        "vmap": {
            "path": "database",
            "hostname": "host",
            "port": "port",
            "username": "user",
            "password": "password",
        },
        "defaults": {"port": 5432},
        "cast": {
            "min_size": int,
            "max_size": int,
            "max_queries": int,
            "max_inactive_connection_lifetime": float,
            "timeout": int,
            "statement_cache_size": int,
            "max_cached_statement_lifetime": int,
            "max_cacheable_statement_size": int,
            "ssl": bool,
        },
    },
    "sqlite": {
        "engine": "tortoise.backends.sqlite",
        "skip_first_char": False,
        "vmap": {"path": "file_path"},
        "defaults": {"journal_mode": "WAL", "journal_size_limit": 16384},
        "cast": {"journal_size_limit": int},
    },
    "mysql": {
        "engine": "tortoise.backends.mysql",
        "vmap": {
            "path": "database",
            "hostname": "host",
            "port": "port",
            "username": "user",
            "password": "password",
        },
        "defaults": {"port": 3306, "charset": "utf8mb4", "sql_mode": "STRICT_TRANS_TABLES"},
        "cast": {
            "minsize": int,
            "maxsize": int,
            "connect_timeout": float,
            "echo": bool,
            "no_delay": bool,
            "use_unicode": bool,
            "pool_recycle": int,
            "ssl": bool,
        },
    },
    "mssql": {
        "engine": "tortoise.backends.mssql",
        "vmap": {
            "path": "database",
            "hostname": "host",
            "port": "port",
            "username": "user",
            "password": "password",
        },
        "defaults": {"port": 1433},
        "cast": {
            "minsize": int,
            "maxsize": int,
            "echo": bool,
            "pool_recycle": int,
        },
    },
    "oracle": {
        "engine": "tortoise.backends.oracle",
        "vmap": {
            "path": "database",
            "hostname": "host",
            "port": "port",
            "username": "user",
            "password": "password",
        },
        "defaults": {"port": 1521},
        "cast": {
            "minsize": int,
            "maxsize": int,
            "echo": bool,
            "pool_recycle": int,
        },
    },
}
# Create an alias for backwards compatibility
DB_LOOKUP["postgres"] = DB_LOOKUP["asyncpg"]


def expand_db_url(db_url: str, testing: bool = False) -> dict:
    url = urlparse.urlparse(db_url)
    if url.scheme not in DB_LOOKUP:
        raise ConfigurationError(f"Unknown DB scheme: {url.scheme}")

    db_backend = url.scheme
    db = DB_LOOKUP[db_backend]
    if db.get("skip_first_char", True):
        path: Optional[str] = url.path[1:]
    else:
        path = url.netloc + url.path

    if not path:
        if db_backend == "sqlite":
            raise ConfigurationError("No path specified for DB_URL")
        # Other database backend accepts database name being None (but not empty string).
        path = None

    params: dict = {}
    for key, val in db["defaults"].items():
        params[key] = val
    for key, val in urlparse.parse_qs(url.query).items():
        cast = db["cast"].get(key, str)
        params[key] = cast(val[-1])

    if testing and path:
        path = path.replace("\\{", "{").replace("\\}", "}")
        path = path.format(uuid.uuid4().hex)

    vmap: dict = {}
    vmap.update(db["vmap"])
    params[vmap["path"]] = path
    if vmap.get("hostname"):
        params[vmap["hostname"]] = url.hostname or None
    try:
        if vmap.get("port") and url.port:
            params[vmap["port"]] = int(url.port)
    except ValueError:
        raise ConfigurationError("Port is not an integer")
    if vmap.get("username"):
        # Pass username as None, instead of empty string,
        # to let asyncpg retrieve username from environment variable or OS user
        params[vmap["username"]] = url.username or None
    if vmap.get("password"):
        # asyncpg accepts None for password, but aiomysql not
        params[vmap["password"]] = (
            None
            if (not url.password and db_backend in {"postgres", "asyncpg", "psycopg"})
            else urlparse.unquote_plus(url.password or "")
        )

    return {"engine": db["engine"], "credentials": params}


def generate_config(
    db_url: str,
    app_modules: Dict[str, Iterable[Union[str, ModuleType]]],
    connection_label: Optional[str] = None,
    testing: bool = False,
) -> dict:
    _connection_label = connection_label or "default"
    return {
        "connections": {_connection_label: expand_db_url(db_url, testing)},
        "apps": {
            app_label: {"models": modules, "default_connection": _connection_label}
            for app_label, modules in app_modules.items()
        },
    }
