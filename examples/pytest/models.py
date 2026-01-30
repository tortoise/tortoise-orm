"""
Example models for pytest testing demonstration.
"""

from tortoise import fields
from tortoise.models import Model


class User(Model):
    """User model for testing."""

    id = fields.IntField(primary_key=True)
    username = fields.CharField(max_length=100, unique=True)
    email = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

    def __str__(self) -> str:
        return self.username


class Post(Model):
    """Post model with foreign key to User."""

    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=255)
    content = fields.TextField()
    author = fields.ForeignKeyField("models.User", related_name="posts")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "posts"

    def __str__(self) -> str:
        return self.title
