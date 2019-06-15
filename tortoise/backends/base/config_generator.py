import urllib.parse as urlparse
import uuid
from typing import Any, Dict, List, Optional  # noqa

from tortoise.exceptions import ConfigurationError

urlparse.uses_netloc.append("postgres")
urlparse.uses_netloc.append("sqlite")
urlparse.uses_netloc.append("mysql")
DB_LOOKUP = {
    "postgres": {
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
        "defaults": {"port": 3306},
        "cast": {
            "minsize": int,
            "maxsize": int,
            "connect_timeout": float,
            "echo": bool,
            "no_delay": bool,
            "use_unicode": bool,
        },
    },
}  # type: Dict[str, Dict[str, Any]]


def expand_db_url(db_url: str, testing: bool = False) -> dict:
    url = urlparse.urlparse(db_url)
    if url.scheme not in DB_LOOKUP:
        raise ConfigurationError("Unknown DB scheme: {}".format(url.scheme))

    db = DB_LOOKUP[url.scheme]
    if db.get("skip_first_char", True):
        path = url.path[1:]
    else:
        path = url.netloc + url.path

    if not path:
        raise ConfigurationError("No path specified for DB_URL")

    params = {}  # type: dict
    for key, val in db["defaults"].items():
        params[key] = val
    for key, val in urlparse.parse_qs(url.query).items():
        cast = db["cast"].get(key, str)
        params[key] = cast(val[-1])

    if testing:
        path = path.replace("\\{", "{").replace("\\}", "}")
        path = path.format(uuid.uuid4().hex)

    vmap = {}  # type: dict
    vmap.update(db["vmap"])
    params[vmap["path"]] = path
    if vmap.get("hostname"):
        params[vmap["hostname"]] = str(url.hostname or "")
    try:
        if vmap.get("port"):
            if url.port:
                params[vmap["port"]] = int(url.port)
    except ValueError:
        raise ConfigurationError("Port is not an integer")
    if vmap.get("username"):
        params[vmap["username"]] = str(url.username or "")
    if vmap.get("password"):
        params[vmap["password"]] = str(url.password or "")

    return {"engine": db["engine"], "credentials": params}


def generate_config(
    db_url: str,
    app_modules: Dict[str, List[str]],
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
