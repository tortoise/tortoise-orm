from __future__ import annotations

from typing import Type

from tortoise.apps import Apps
from tortoise.connection import connections
from tortoise.models import Model


class StateApps(Apps):
    def __init__(self) -> None:
        super().__init__({}, connections)

    def register_model(self, app_label: str, model: Type[Model]) -> None:
        if app_label not in self.apps:
            self.apps[app_label] = {}

        if model._meta.app and model._meta.app != app_label:
            raise ValueError(
                f"Given model is already registered with label {model._meta.app}"
            )

        self.apps[app_label][model.__name__] = model
        model._meta.app = app_label

    def unregister_model(self, app_label: str, model_name: str) -> None:
        try:
            model = self.apps[app_label].pop(model_name)
            model._meta.app = None
        except KeyError:
            return

    def split_reference(self, reference: str | Type[Model]) -> tuple[str, str]:
        if not isinstance(reference, str):
            model_class = reference
            return model_class._meta.app, model_class.__name__
        if len(items := reference.split(".")) != 2:
            raise ValueError(
                f"'{reference}' is not a valid model reference. Should be <app>.<model>."
            )
        return items[0], items[1]

    def get_model(self, reference: str) -> Type[Model]:
        app_label, model_name = self.split_reference(reference)
        return self.apps[app_label][model_name]

    def clone(self) -> "StateApps":
        from tortoise.migrations.schema_generator.state import ModelState

        state_apps = self.__class__()
        for app_label, app in self.apps.items():
            for model in app.values():
                model_clone = ModelState.make_from_model(app_label, model).render(state_apps)
                state_apps.register_model(app_label, model_clone)

        return state_apps
