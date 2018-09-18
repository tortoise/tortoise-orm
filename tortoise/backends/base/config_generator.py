import urllib.parse as urlparse
import uuid
from typing import Any, Dict, List, Optional  # noqa

from tortoise.exceptions import ConfigurationError

urlparse.uses_netloc.append('postgres')
urlparse.uses_netloc.append('sqlite')
urlparse.uses_netloc.append('mysql')
DB_LOOKUP = {
    'postgres': {
        'engine': 'tortoise.backends.asyncpg',
        'vars': {
            'path': 'database',
            'hostname': 'host',
            'port': 'port',
            'username': 'user',
            'password': 'password',
        },
    },
    'sqlite': {
        'engine': 'tortoise.backends.sqlite',
        'skip_first_char': False,
        'vars': {
            'path': 'file_path',
        },
    },
    'mysql': {
        'engine': 'tortoise.backends.mysql',
        'vars': {
            'path': 'database',
            'hostname': 'host',
            'port': 'port',
            'username': 'user',
            'password': 'password',
        },
    },
}  # type: Dict[str, Dict[str, Any]]


def expand_db_url(db_url: str, testing: bool = False) -> dict:
    url = urlparse.urlparse(db_url)
    if url.scheme not in DB_LOOKUP:
        raise ConfigurationError('Unknown DB scheme: {}'.format(url.scheme))

    db = DB_LOOKUP[url.scheme]
    if db.get('skip_first_char', True):
        path = url.path[1:]
    else:
        path = url.path + url.netloc

    if not path:
        raise ConfigurationError('No path specified for DB_URL')

    params = {}  # type: dict
    for key, val in urlparse.parse_qs(url.query).items():
        params[key] = val[-1]

    if testing:
        params['single_connection'] = True
        path = path.replace('\\{', '{').replace('\\}', '}')
        path = path.format(uuid.uuid4().hex)

    vars = {}  # type: dict
    vars.update(db['vars'])
    params[vars['path']] = path
    if vars.get('hostname'):
        params[vars['hostname']] = str(url.hostname or '')
    try:
        if vars.get('port'):
            params[vars['port']] = str(url.port or '')
    except ValueError:
        raise ConfigurationError('Port is not an integer')
    if vars.get('username'):
        params[vars['username']] = str(url.username or '')
    if vars.get('password'):
        params[vars['password']] = str(url.password or '')

    return {
        'engine': db['engine'],
        'credentials': params,
    }


def generate_config(
        db_url: str,
        app_modules: Dict[str, List[str]],
        connection_label: Optional[str] = None,
        testing: bool = False,
) -> dict:
    _connection_label = connection_label or 'default'
    return {
        'connections': {
            _connection_label: expand_db_url(db_url, testing)
        },
        'apps': {
            app_label: {
                'models': modules,
                'default_connection': _connection_label,
            }
            for app_label, modules in app_modules.items()
        }
    }
