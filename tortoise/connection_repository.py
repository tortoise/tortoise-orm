from typing import Dict, Iterable

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import ConfigurationError


class ConnectionRepository:
    def __init__(self) -> None:
        self.connections: Dict[str, BaseDBAsyncClient] = {}

    def register(self, name: str, connection: BaseDBAsyncClient):
        if name in self.connections:
            raise ConfigurationError(f'Connection with name "{name}" already registered')
        self.connections[name] = connection

    def unregister(self, name: str):
        if name not in self.connections:
            raise ConfigurationError(f'Unknown connection "{name}"')

    def get(self, name: str, default: None = None):
        return self.connections.get(name, default)

    def copy(self) -> "ConnectionRepository":
        repo = ConnectionRepository()
        repo.connections = self.connections.copy()
        return repo

    def get_connections(self) -> Iterable[BaseDBAsyncClient]:
        return self.connections.values()

    def __getitem__(self, key):
        return self.connections[key]

    def __len__(self):
        return len(self.connections)

    def __repr__(self):
        return f"ConnectionRepository: {self.connections}"
