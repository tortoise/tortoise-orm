"""
This is the testing Models — Cyclic
"""
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament = fields.ManyToManyField("Two")
