"""
This is the testing Models — Cyclic
"""
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament = fields.ForeignKeyField("models.Two", related_name="events")


class Two(Model):
    tournament = fields.ForeignKeyField("models.Three", related_name="events")


class Three(Model):
    tournament = fields.ForeignKeyField("models.One", related_name="events")
