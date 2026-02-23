from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from tortoise.migrations.schema_generator.state import ModelState

from pypika_tortoise import Query, Table

from tortoise.apps import Apps
from tortoise.connection import ConnectionHandler
from tortoise.context import get_current_context
from tortoise.models import Model


class StateApps(Apps):
    def __init__(
        self,
        default_connections: dict[str, str] | None = None,
        connections: ConnectionHandler | None = None,
    ) -> None:
        if connections is None:
            ctx = get_current_context()
            connections = ctx.connections if ctx is not None else ConnectionHandler()

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

    def _init_relations(self) -> None:
        """Override to gracefully skip relations whose target model hasn't been
        registered yet.  This happens when ``CreateModel`` operations are sorted
        alphabetically and a model with a FK is processed before the FK target.
        Models with unresolved relations are left with ``_inited = False`` so
        they will be fully initialised on the next ``_reload`` call once the
        target model exists."""
        uninited_models: list[type[Model]] = []
        for app in self.apps.values():
            for model in app.values():
                if not model._meta._inited:
                    uninited_models.append(model)

        if not uninited_models:
            return

        models_with_missing_refs: set[type[Model]] = set()

        for model in uninited_models:
            for field_name in (*model._meta.fk_fields, *model._meta.o2o_fields):
                fk_object = model._meta.fields_map[field_name]
                reference = fk_object.model_name  # type: ignore[attr-defined]
                if isinstance(reference, str):
                    parts = reference.split(".")
                    if len(parts) == 2:
                        ref_app, ref_model = parts
                        if ref_app not in self.apps or ref_model not in self.apps.get(ref_app, {}):
                            models_with_missing_refs.add(model)
                            break  # No need to check remaining fields

            if model in models_with_missing_refs:
                continue

            for field_name in model._meta.m2m_fields:
                m2m_object = model._meta.fields_map[field_name]
                reference = m2m_object.model_name  # type: ignore[attr-defined]
                if isinstance(reference, str):
                    parts = reference.split(".")
                    if len(parts) == 2:
                        ref_app, ref_model = parts
                        if ref_app not in self.apps or ref_model not in self.apps.get(ref_app, {}):
                            models_with_missing_refs.add(model)
                            break

        for model in models_with_missing_refs:
            model._meta._inited = True

        super()._init_relations()

        for model in models_with_missing_refs:
            model._meta._inited = False

    def _build_initial_querysets(self) -> None:
        # Skip building querysets when no DB config is available (state-only mode)
        # This allows pure state operations to work without database connections
        if self._connections._db_config is None:
            return

        for app in self.apps.values():
            for model in app.values():
                if model._meta.default_connection is None:
                    continue
                if not model._meta._inited:
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

    def clone(
        self,
        model_states: dict[tuple[str, str], ModelState] | None = None,
    ) -> StateApps:
        from tortoise.migrations.schema_generator.state import ModelState

        state_apps = self.__class__(
            default_connections=dict(self._default_connections),
            connections=self._connections,
        )
        if model_states is not None:
            for (app_label, _model_name), model_state in model_states.items():
                model = model_state.render(state_apps, deepcopy_fields=False)
                state_apps.register_model(app_label, model)
        else:
            for app_label, app in self.apps.items():
                for model in app.values():
                    model_clone = ModelState.make_from_model(app_label, model).render(state_apps)
                    state_apps.register_model(app_label, model_clone)

        state_apps._init_relations()
        state_apps._build_initial_querysets()
        return state_apps
