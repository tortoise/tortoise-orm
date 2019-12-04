"""
This is the testing Models — Generated non-int PK
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    val = fields.CharField(max_length=50, pk=True, generated=True)
