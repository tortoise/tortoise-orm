import typing

if typing.TYPE_CHECKING:
    from tortoise.fields import Field


class BaseORMException(Exception):
    """
    Base ORM Exception.
    """


class FieldError(BaseORMException):
    """
    The FieldError exception is raised when there is a problem with a model field.
    """


class ParamsError(BaseORMException):
    """
    The ParamsError is raised when function can not be run with given parameters
    """


class ConfigurationError(BaseORMException):
    """
    The ConfigurationError exception is raised when the configuration of the ORM is invalid.
    """


class TransactionManagementError(BaseORMException):
    """
    The TransactionManagementError is raised when any transaction error occurs.
    """


class OperationalError(BaseORMException):
    """
    The OperationalError exception is raised when an operational error occurs.
    """


class IntegrityError(OperationalError):
    """
    The IntegrityError exception is raised when there is an integrity error.
    """


class NoValuesFetched(OperationalError):
    """
    The NoValuesFetched exception is raised when the related model was never fetched.
    """


class MultipleObjectsReturned(OperationalError):
    """
    The MultipleObjectsReturned exception is raised when doing a ``.get()`` operation,
    and more than one object is returned.
    """


class DoesNotExist(OperationalError):
    """
    The DoesNotExist exception is raised when expecting data, such as a ``.get()`` operation.
    """


class IncompleteInstanceError(OperationalError):
    """
    The IncompleteInstanceError exception is raised when a partial model is attempted to be persisted.
    """


class DBConnectionError(BaseORMException, ConnectionError):
    """
    The DBConnectionError is raised when problems with connecting to db occurs
    """


class ValidationError(BaseORMException):
    """
    The ValidationError is raised when validators of field validate failed.
    """


class UnSupportedError(BaseORMException):
    """
    The UnSupportedError is raised when operation is not supported.
    """


class FieldValidationError(ValidationError):
    """
    The FieldValidationError is raised when validators of field validate failed.
    """

    def __init__(self, field: "Field", msg: str):
        self.field = field
        self.msg = msg

    def __str__(self):
        return self.msg
