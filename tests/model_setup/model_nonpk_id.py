"""
This is the testing Models — Model with field id, but NO PK
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.CharField(max_length=50)
