"""
This is the testing Models — FK bad model name
"""
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament = fields.ForeignKeyField("moo")
