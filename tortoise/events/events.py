from typing import Type, Dict, Callable

from tortoise.events import NoSuchEventError


class EventListMeta(type):

    def __contains__(self, event: Callable):
        """Checks if the event (by name) exists on the events list."""
        event_name = event.__name__
        try:
            return event is getattr(self, event_name)
        except NoSuchEventError:
            return False

    def __getattr__(self, item):
        """Intercepts getattribute and raises if the event does not exist."""
        raise NoSuchEventError()


class EventList(metaclass=EventListMeta):
    """
    Contains a list of emittable events.
    Events are defined as functions on a subclass
    of the EventList type, and their signatures
    used to determine the "contract" of the event.
    """


class AsyncEventList(EventList):
    """
    Signifies a list of async events.
    """


class ExecutorEvents(AsyncEventList):

    @staticmethod
    async def before_select(query, custom_fields):
        pass

    @staticmethod
    async def before_insert(query, values):
        pass

    async def update(self):
        pass

    async def delete(self):
        pass


class TableEvents(AsyncEventList):

    async def before_create(self):
        pass

    async def after_create(self):
        pass

    async def before_drop(self):
        pass

    async def after_drop(self):
        pass


class TableGenerationEvents(EventList):

    @staticmethod
    def before_generate_sql(for_model: Type):
        """Called when the SQL for a table is generated."""

    @staticmethod
    def after_generate_sql(table_data: Dict):
        """
        Called when the SQL for a table is generated.

        :param table_data: A dictionary which contains the data for the table.
            - table: The name of the table in the database
            - model: The class of the model that it represents
            - table_creation_string: The string to create the table in the DB
            - references: The foreign keys
            - m2m_tables: The m2m tables
        """


class ConnectionEvents(AsyncEventList):

    @staticmethod
    async def connecting(user, password, host, port, database):
        """Called when a connection is being opened."""

    @staticmethod
    async def connected(connection):
        """Called when the given connection has just been opened."""

    @staticmethod
    async def closing(connection):
        """Called when a database connection is closing."""

    @staticmethod
    async def db_created(database, user):
        """Called when a database is created."""

    @staticmethod
    async def db_deleted(database):
        """Called when a database is deleted."""
