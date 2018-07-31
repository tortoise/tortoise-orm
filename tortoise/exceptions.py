__all__ = ('BaseORMException', 'FieldError', 'ConfigurationError', 'TransactionManagementError',
           'OperationalError', 'IntegrityError', 'NoValuesFetched', 'MultipleObjectsReturned',
           'DoesNotExist')


class BaseORMException(Exception):
    """
    Base ORM Exception.
    """
    pass


class FieldError(BaseORMException):
    """
    The FieldError exception is raised when there is a problem with a model field.
    """
    pass


class ParamsError(BaseORMException):
    """
    The ParamsError is raised when function can not be run with given parameters
    """
    pass


class ConfigurationError(BaseORMException):
    """
    The ConfigurationError exception is raised when the configuration of the ORM is invalid.
    """
    pass


class TransactionManagementError(BaseORMException):
    """
    The TransactionManagementError is raised when any transaction error occurs.
    """
    pass


class OperationalError(BaseORMException):
    """
    The OperationalError exception is raised when an operational error occurs.
    """
    pass


class IntegrityError(OperationalError):
    """
    The IntegrityError exception is raised when there is an integrity error.
    """
    pass


class NoValuesFetched(OperationalError):
    """
    The NoValuesFetched exception is raised when the related model was never fetched.
    """
    pass


class MultipleObjectsReturned(OperationalError):
    """
    The MultipleObjectsReturned exception is raised when doing a ``.get()`` operation,
    and more than one object is returned.
    """
    pass


class DoesNotExist(OperationalError):
    """
    The DoesNotExist exception is raised when expecting data, such as a ``.get()`` operation.
    """
    pass


class DBConnectionError(BaseORMException):
    """
    The DBConnectionError is raised when problems with connecting to db occurs
    """
    pass
