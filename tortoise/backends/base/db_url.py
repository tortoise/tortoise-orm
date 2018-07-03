import urllib.parse as urlparse
import uuid

from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.sqlite.client import SqliteClient

urlparse.uses_netloc.append('postgres')
urlparse.uses_netloc.append('sqlite')
DB_LOOKUP = {
    'postgres': {
        'client': AsyncpgDBClient,
        'vars': {
            'path': 'database',
            'hostname': 'host',
            'port': 'port',
            'username': 'user',
            'password': 'password',
        },
        'test_defaults': {
            'single_connection': True
        },
    },
    'sqlite': {
        'client': SqliteClient,
        'skip_first_char': False,
        'vars': {
            'path': 'filename',
        },
    },
}


def expand_db_url(db_url: str, testing: bool = False) -> dict:
    url = urlparse.urlparse(db_url)
    db = DB_LOOKUP[url.scheme]
    if db.get('skip_first_char', True):
        path = url.path[1:]
    else:
        path = url.path
    if '?' in path and not url.query:
        path, query = path.split('?', 2)
    else:
        path, query = path, url.query

    params = {}  # type: dict
    params.update(db.get('test_defaults', {}))  # type: ignore
    for key, val in urlparse.parse_qs(query).items():
        params[key] = val[-1]

    if testing:
        params['single_connection'] = True
        path = path.replace('\\{', '{').replace('\\}', '}')
        path = path.format(uuid.uuid4().hex)

    vars = {}  # type: dict
    vars.update(db.get('vars', {}))  # type: ignore
    if vars.get('path'):
        params[vars['path']] = path
    if vars.get('hostname'):
        params[vars['hostname']] = str(url.hostname or '')
    if vars.get('port'):
        params[vars['port']] = str(url.port or '')
    if vars.get('username'):
        params[vars['username']] = str(url.username or '')
    if vars.get('password'):
        params[vars['password']] = str(url.password or '')

    return {
        'params': params,
        'client': db['client'],
    }
