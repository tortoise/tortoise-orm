"""
This is the testing Models — Multi ManyToMany fields
"""

from __future__ import annotations

from tortoise import Model, fields


class One(Model):
    threes: fields.ManyToManyRelation[Three]


class Two(Model):
    threes: fields.ManyToManyRelation[Three]


class Three(Model):
    ones: fields.ManyToManyRelation[One] = fields.ManyToManyField("models.One")
    twos: fields.ManyToManyRelation[Two] = fields.ManyToManyField("models.Two")
