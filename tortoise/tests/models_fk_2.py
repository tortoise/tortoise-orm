"""
This is the testing Models — Bad on_delete parameter
"""
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament = fields.ForeignKeyField("models.Two", on_delete="WABOOM")
