import logging
import sqlite3
import uuid


def get_db_name():
    db_id = uuid.uuid4().hex
    name = '/tmp/test-{}.sqlite'.format(db_id)
    return name
