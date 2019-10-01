"""
This is the testing Models — Multiple PK
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    id2 = fields.IntField(pk=True)
