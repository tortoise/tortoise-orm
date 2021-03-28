"""
This is the testing Models
"""
from tortoise import fields
from tortoise.models import Model


class AuthorMultipeName(Model):
    name = fields.CharField(max_length=255)


class Author(Model):
    name = fields.CharField(max_length=255)
