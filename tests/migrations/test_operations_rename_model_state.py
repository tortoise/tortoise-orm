from __future__ import annotations

from tortoise import fields
from tortoise.migrations.operations import CreateModel, RenameModel
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps


def test_rename_model_unregisters_old_state() -> None:
    state = State(models={}, apps=StateApps())
    create = CreateModel(
        name="Author",
        fields=[("id", fields.IntField(pk=True))],
        options={"app": "blog", "table": "author", "pk_attr": "id"},
        bases=["Model"],
    )
    create.state_forward("blog", state)
    assert ("blog", "Author") in state.models
    assert "Author" in state.apps.apps.get("blog", {})

    rename = RenameModel(old_name="Author", new_name="Writer")
    rename.state_forward("blog", state)

    assert ("blog", "Author") not in state.models
    assert "Author" not in state.apps.apps.get("blog", {})
    assert ("blog", "Writer") in state.models
    assert "Writer" in state.apps.apps.get("blog", {})
