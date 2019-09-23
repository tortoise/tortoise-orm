"""
'Failure' tests for __models__
"""

from tortoise import fields
from tortoise.models import Model


class BadTournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True, index=True)

    def __str__(self):
        return self.name


class GoodTournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True, index=True)

    def __str__(self):
        return self.name


class Tmp:
    class InAClassTournament(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        created = fields.DatetimeField(auto_now_add=True, index=True)

        def __str__(self):
            return self.name


__models__ = [BadTournament]
