from __future__ import annotations

from tortoise import fields, models


class Author(models.Model):
    id = fields.IntField(pk=True)
    full_name = fields.CharField(max_length=200, source_field="name")

    def __str__(self) -> str:
        return self.full_name


class Post(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=300)
    slug = fields.CharField(max_length=220, unique=True)
    body = fields.TextField(source_field="content")
    excerpt = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    author: fields.ForeignKeyRelation[Author] = fields.ForeignKeyField(
        "blog.Author", related_name="posts"
    )
    categories: fields.ManyToManyRelation[Category] = fields.ManyToManyField(
        "blog.Category", related_name="posts"
    )
    tags: fields.ManyToManyRelation[Tag] = fields.ManyToManyField("blog.Tag", related_name="posts")

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    id = fields.IntField(pk=True)
    post: fields.ForeignKeyRelation[Post] = fields.ForeignKeyField(
        "blog.Post", related_name="comments"
    )
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)


class State(models.Model):
    id = fields.IntField(pk=True)
    code = fields.CharField(max_length=20, unique=True)

    class Meta:
        table = "status"


class Category(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=120, unique=True)


class Tag(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=80, unique=True)
