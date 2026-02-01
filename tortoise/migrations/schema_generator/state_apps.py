from __future__ import annotations

from typing import cast

from pypika_tortoise import Query, Table

from tortoise.apps import Apps
from tortoise.connection import connections
from tortoise.models import Model


class StateApps(Apps):
    def __init__(self, default_connections: dict[str, str] | None = None) -> None:
        super().__init__({}, connections)
        self._default_connections = default_connections or {}

    def register_model(self, app_label: str, model: type[Model]) -> None:
        if app_label not in self.apps:
            self.apps[app_label] = {}

        if model._meta.app and model._meta.app != app_label:
            raise ValueError(f"Given model is already registered with label {model._meta.app}")

        self.apps[app_label][model.__name__] = model
        model._meta.app = app_label
        if app_label in self._default_connections:
            model._meta.default_connection = self._default_connections[app_label]

    def _build_initial_querysets(self) -> None:
        for app in self.apps.values():
            for model in app.values():
                if model._meta.default_connection is None:
                    continue
                model._meta.finalise_model()
                model._meta.basetable = Table(name=model._meta.db_table, schema=model._meta.schema)
                basequery = model._meta.db.query_class.from_(model._meta.basetable)
                model._meta.basequery = cast(Query, basequery)
                model._meta.basequery_all_fields = cast(
                    Query, basequery.select(*model._meta.db_fields)
                )

    def unregister_model(self, app_label: str, model_name: str) -> None:
        try:
            model = self.apps[app_label].pop(model_name)
            model._meta.app = None
        except KeyError:
            return

    def split_reference(self, reference: str | type[Model]) -> tuple[str, str]:
        if not isinstance(reference, str):
            model_class = reference
            app_label = model_class._meta.app
            if app_label is None:
                raise ValueError(f"Model {model_class} is not registered in any app")
            return app_label, model_class.__name__
        if len(items := reference.split(".")) != 2:
            raise ValueError(
                f"'{reference}' is not a valid model reference. Should be <app>.<model>."
            )
        return items[0], items[1]

    def get_model(self, app_label: str, model_name: str | None = None) -> type[Model]:
        if model_name is None:
            app_label, model_name = self.split_reference(app_label)
        return self.apps[app_label][model_name]

    def clone(self) -> StateApps:
        from tortoise.migrations.schema_generator.state import ModelState

        state_apps = self.__class__(default_connections=dict(self._default_connections))
        for app_label, app in self.apps.items():
            for model in app.values():
                model_clone = ModelState.make_from_model(app_label, model).render(state_apps)
                state_apps.register_model(app_label, model_clone)

        state_apps._init_relations()
        state_apps._build_initial_querysets()
        return state_apps
