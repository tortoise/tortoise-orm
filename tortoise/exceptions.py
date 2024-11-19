from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from tortoise import Model, Type


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


class NotExistOrMultiple(OperationalError):
    TEMPLATE = ""

    def __init__(self, model: "Union[Type[Model], str]", *args) -> None:
        self.model: "Optional[Type[Model]]" = None
        if isinstance(model, str):
            args = (model,) + args
        else:
            self.model = model
        super().__init__(*args)

    def __str__(self) -> str:
        if self.model is None:
            return super().__str__()
        return self.TEMPLATE.format(self.model.__name__)


class MultipleObjectsReturned(NotExistOrMultiple):
    """
    The MultipleObjectsReturned exception is raised when doing a ``.get()`` operation,
    and more than one object is returned.
    """

    TEMPLATE = 'Multiple objects returned for "{}", expected exactly one'


class ObjectDoesNotExistError(OperationalError, KeyError):
    """
    The DoesNotExist exception is raised when an item with the passed primary key does not exist
    """

    def __init__(self, model: "Type[Model]", pk_name: str, pk_val: Any) -> None:
        self.model: "Type[Model]" = model
        self.pk_name: str = pk_name
        self.pk_val: Any = pk_val

    def __str__(self) -> str:
        return f"{self.model.__name__} has no object with {self.pk_name}={self.pk_val}"


class DoesNotExist(NotExistOrMultiple):
    """
    The DoesNotExist exception is raised when expecting data, such as a ``.get()`` operation.
    """

    TEMPLATE = 'Object "{}" does not exist'


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
