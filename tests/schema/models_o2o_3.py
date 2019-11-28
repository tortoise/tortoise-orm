"""
This is the testing Models — on_delete SET_NULL without null=True
"""
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament = fields.OneToOneField("models.Two", on_delete=fields.SET_NULL)
