from typing import TYPE_CHECKING, List, Optional, Type

from tortoise.connection import connections
from tortoise.exceptions import ConfigurationError

if TYPE_CHECKING:
    from tortoise import BaseDBAsyncClient, Model


class ConnectionRouter:
    def __init__(self) -> None:
        self._routers: List[type] = None  # type: ignore

    def init_routers(self, routers: List[type]):
        self._routers = [r() for r in routers]

    def _router_func(self, model: Type["Model"], action: str):
        for r in self._routers:
            try:
                method = getattr(r, action)
            except AttributeError:
                # If the router doesn't have a method, skip to the next one.
                pass
            else:
                chosen_db = method(model)
                if chosen_db:
                    return chosen_db

    def _db_route(self, model: Type["Model"], action: str):
        try:
            return connections.get(self._router_func(model, action))
        except ConfigurationError:
            return None

    def db_for_read(self, model: Type["Model"]) -> Optional["BaseDBAsyncClient"]:
        return self._db_route(model, "db_for_read")

    def db_for_write(self, model: Type["Model"]) -> Optional["BaseDBAsyncClient"]:
        return self._db_route(model, "db_for_write")


router = ConnectionRouter()
