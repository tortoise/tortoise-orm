from __future__ import annotations

from typing import Any, cast

from tortoise import fields
from tortoise.context import TortoiseContext
from tortoise.fields.relational import ForeignKeyFieldInstance
from tortoise.migrations.operations import CreateModel
from tortoise.migrations.schema_generator.state import ModelState, State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


def test_model_state_skips_fk_reference_fields() -> None:
    class Author(Model):
        id = fields.IntField(pk=True)

        class Meta:
            app = "blog"

    class Post(Model):
        id = fields.IntField(pk=True)
        author: ForeignKeyFieldInstance[Any] = fields.ForeignKeyField(
            "blog.Author", related_name="posts"
        )

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


def test_state_apps_builds_relations_before_querysets() -> None:
    with TortoiseContext() as ctx:
        ctx.connections._init_config(
            {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": ":memory:"},
                }
            }
        )
        state = State(models={}, apps=StateApps(default_connections={"blog": "default"}))
        CreateModel(
            name="Author",
            fields=[("id", fields.IntField(pk=True))],
        ).state_forward("blog", state)
        CreateModel(
            name="Post",
            fields=[
                ("id", fields.IntField(pk=True)),
                ("author", fields.ForeignKeyField("blog.Author", related_name="posts")),
            ],
        ).state_forward("blog", state)

        post_model = state.apps.get_model("blog.Post")
        author_field = cast(ForeignKeyFieldInstance, post_model._meta.fields_map["author"])
        assert author_field.to_field_instance is not None
