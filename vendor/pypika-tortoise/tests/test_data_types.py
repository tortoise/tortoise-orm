import unittest
import uuid

from pypika.terms import ValueWrapper


class StringTests(unittest.TestCase):
    def test_inline_string_concatentation(self):
        self.assertEqual("'it''s'", ValueWrapper("it's").get_sql())


class UuidTests(unittest.TestCase):
    def test_uuid_string_generation(self):
        id = uuid.uuid4()
        self.assertEqual("'{}'".format(id), ValueWrapper(id).get_sql())
