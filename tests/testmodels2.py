"""
This is the testing Models
"""
from tortoise import fields
from tortoise.models import Model


class Author(Model):
    name = fields.CharField(max_length=255)
