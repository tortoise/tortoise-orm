"""
This is the testing Models — FK bad model name
"""

from __future__ import annotations

from typing import Any

from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament: fields.ForeignKeyRelation[Any] = fields.ForeignKeyField("moo")
