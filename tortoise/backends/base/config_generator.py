from __future__ import annotations

import urllib.parse as urlparse
import uuid
from collections.abc import Iterable
from types import ModuleType
from typing import Any

from tortoise.exceptions import ConfigurationError

urlparse.uses_netloc.append("postgres")
urlparse.uses_netloc.append("asyncpg")
urlparse.uses_netloc.append("psycopg")
urlparse.uses_netloc.append("sqlite")
urlparse.uses_netloc.append("mysql")
urlparse.uses_netloc.append("oracle")
urlparse.uses_netloc.append("mssql")
DB_LOOKUP: dict[str, dict[str, Any]] = {
    "psycopg": {
        "engine": "tortoise.backends.psycopg",
        "vmap": {
            "path": "database",
            "hostname": "host",
            "port": "port",
            "username": "user",
            "password": "password",  # nosec:B105
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
            "password": "password",  # nosec:B105
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
        "cast": {
            "journal_size_limit": int,
            "install_regexp_functions": bool,
        },
    },
    "mysql": {
        "engine": "tortoise.backends.mysql",
        "vmap": {
            "path": "database",
            "hostname": "host",
            "port": "port",
            "username": "user",
            "password": "password",  # nosec:B105
        },
        "defaults": {"port": 3306, "charset": "utf8mb4", "sql_mode": "STRICT_TRANS_TABLES"},
        "cast": {
            "minsize": int,
            "maxsize": int,
            "connect_timeout": float,
            "echo": bool,
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
            "password": "password",  # nosec:B105
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
            "password": "password",  # nosec:B105
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


def _quote_url_userinfo(db_url: str) -> str:
    """Quote special characters in username and password to avoid URL parsing issues.

    urlparse fails when passwords contain characters like '[' or ']' because it
    tries to parse them as IPv6 addresses. This function percent-encodes the userinfo
    part (username:password) while leaving the rest of the URL intact.

    Only characters that cause parsing issues (like '[' and ']') are encoded.
    Already percent-encoded sequences (like %25) are preserved.
    """
    # Find the scheme delimiter
    scheme_end = db_url.find("://")
    if scheme_end == -1:
        return db_url

    scheme = db_url[: scheme_end + 3]  # Include "://"
    rest = db_url[scheme_end + 3 :]

    # Find the userinfo section (everything before @)
    at_pos = rest.find("@")
    if at_pos == -1:
        # No credentials
        return db_url

    userinfo = rest[:at_pos]
    after_userinfo = rest[at_pos:]

    # Split userinfo into username and password
    colon_pos = userinfo.find(":")
    if colon_pos == -1:
        # No password, just username
        # Only quote characters that cause parsing issues
        username = urlparse.quote(userinfo, safe="%")
        return scheme + username + after_userinfo
    else:
        username = userinfo[:colon_pos]
        password = userinfo[colon_pos + 1 :]
        # Quote username and password, but preserve already-encoded sequences
        # We keep % as safe so existing percent-encoded chars aren't double-encoded
        username_quoted = urlparse.quote(username, safe="%")
        password_quoted = urlparse.quote(password, safe="%")
        return scheme + username_quoted + ":" + password_quoted + after_userinfo


def expand_db_url(db_url: str, testing: bool = False) -> dict:
    # Quote special characters in userinfo to avoid parsing errors
    db_url = _quote_url_userinfo(db_url)
    url = urlparse.urlparse(db_url)
    if url.scheme not in DB_LOOKUP:
        raise ConfigurationError(f"Unknown DB scheme: {url.scheme}")

    db_backend = url.scheme
    db = DB_LOOKUP[db_backend]
    if db.get("skip_first_char", True):
        path: str | None = url.path[1:]
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
    app_modules: dict[str, Iterable[str | ModuleType]],
    connection_label: str | None = None,
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
