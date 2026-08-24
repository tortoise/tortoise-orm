"""
This example demonstrates SQL Schema generation for fields that set a db_collation.
"""

from tortoise import fields
from tortoise.models import Model


class Account(Model):
    name = fields.CharField(max_length=50, db_collation="NOCASE")
    bio = fields.TextField(db_collation="NOCASE")
    plain = fields.CharField(max_length=20)
