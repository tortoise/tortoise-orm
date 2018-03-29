import logging
import sqlite3
import uuid


def create_example_database():
    db_id = uuid.uuid4().hex
    name = '/tmp/test-{}.sqlite'.format(db_id)
    connection = sqlite3.connect(name)
    cursor = connection.cursor()
    with open('example_database.sql', 'r') as f:
        cursor.executescript(f.read())
    cursor.close()
    connection.close()
    return name
