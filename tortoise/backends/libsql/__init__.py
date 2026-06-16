from .client import LibsqlClient

client_class = LibsqlClient


def get_client_class(db_info: dict):
    return LibsqlClient
