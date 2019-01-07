from tortoise.exceptions import BaseORMException


class NoSuchListenerError(BaseORMException):
    pass


class NoSuchEventError(AttributeError):
    pass


class InvalidHandlerError(BaseORMException):
    pass
