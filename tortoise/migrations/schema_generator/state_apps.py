from typing import Type

from tortoise import Apps, ConnectionRepository, Model
from tortoise.apps import TortoiseApplication


class StateApps(Apps):
    def __init__(self) -> None:
        super().__init__({}, ConnectionRepository())

    def register_model(self, app_label: str, model: Type[Model]):
        if app_label not in self.apps:
            self.apps[app_label] = TortoiseApplication(app_label, [])

        if model._meta.app is not None:
            raise ValueError(
                f"Given model is already registered with label {model._meta.app}"
            )

        self.apps[app_label].models[model.__name__] = model
        model._meta.app = app_label

    def unregister_model(self, app_label: str, model_name: str):
        try:
            model = self.apps[app_label].models.pop(model_name)
            model._meta.app = None
        except KeyError:
            pass

    def clone(self) -> "StateApps":
        from tortoise.migrations.schema_generator.state import ModelState

        state_apps = self.__class__()
        for app_label, app in self.apps.items():
            for model in app.models.values():
                model_clone = ModelState.make_from_model(app_label, model).render(
                    state_apps
                )
                state_apps.register_model(app_label, model_clone)

        return state_apps
