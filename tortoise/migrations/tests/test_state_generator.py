from __future__ import annotations

from tortoise import fields
from tortoise.migrations.schema_generator.state import ModelState
from tortoise.models import Model


def test_model_state_skips_fk_reference_fields() -> None:
    class Author(Model):
        id = fields.IntField(pk=True)

        class Meta:
            app = "blog"

    class Post(Model):
        id = fields.IntField(pk=True)
        author = fields.ForeignKeyField("blog.Author", related_name="posts")

        class Meta:
            app = "blog"

    state = ModelState.make_from_model("blog", Post)
    assert "author" in state.fields
    assert "author_id" not in state.fields


def test_field_signature_ignores_implicit_db_column() -> None:
    field = fields.CharField(max_length=100)
    field.model_field_name = ""
    field.source_field = None
    from tortoise.migrations.schema_generator.state_diff import _field_signature

    signature = _field_signature(field)
    assert "db_column" not in signature
