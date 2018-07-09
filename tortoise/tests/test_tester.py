from datetime import date, datetime, timedelta
from decimal import Decimal
from time import sleep

from tortoise import fields
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.tests import testmodels


class TestTesterSync(test.TestCase):

    def setUp(self):
        self.moo = 'SET'

    def tearDown(self):
        self.assertEqual(self.moo, 'SET')

    def test_moo(self):
        self.assertEqual(self.moo, 'SET')


class TestTesterASync(test.TestCase):

    async def setUp(self):
        self.baa = 'TES'

    async def tearDown(self):
        self.assertEqual(self.baa, 'TES')

    async def test_moo(self):
        self.assertEqual(self.baa, 'TES')
