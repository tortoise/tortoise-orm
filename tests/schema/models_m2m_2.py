"""
This is the testing Models — Multi ManyToMany fields
"""

from __future__ import annotations

from tortoise import Model, fields
from tortoise.fields import CASCADE


class One(Model):
    threes: fields.ManyToManyRelation[Three]


class Two(Model):
    threes: fields.ManyToManyRelation[Three]


class Three(Model):
    ones: fields.ManyToManyRelation[One] = fields.ManyToManyField("models.One", on_delete=CASCADE)
    twos: fields.ManyToManyRelation[Two] = fields.ManyToManyField("models.Two", on_delete=CASCADE)
