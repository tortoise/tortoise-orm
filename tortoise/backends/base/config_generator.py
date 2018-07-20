import urllib.parse as urlparse
import uuid
from typing import Any, Dict, List  # noqa

from tortoise.exceptions import ConfigurationError

urlparse.uses_netloc.append('postgres')
urlparse.uses_netloc.append('sqlite')
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
}  # type: Dict[str, Dict[str, Any]]


def generate_config(
        db_url: str,
        model_modules: List[str],
        app_label: str,
        testing: bool = False,
) -> dict:
    if not app_label:
        app_label = 'models_{}'.format(uuid.uuid4().hex)
    url = urlparse.urlparse(db_url)
    if url.scheme not in DB_LOOKUP:
        raise ConfigurationError('Unknown DB scheme: {}'.format(url.scheme))

    db = DB_LOOKUP[url.scheme]
    if db.get('skip_first_char', True):
        path = url.path[1:]
    else:
        path = url.path

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
        'connections': {
            app_label: {
                'engine': db['engine'],
                'credentials': params,
            }
        },
        'apps': {
            app_label: {
                'models': model_modules,
                'default_connection': app_label,
            },
        }
    }
