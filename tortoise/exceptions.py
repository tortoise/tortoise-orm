class BaseORMException(Exception):
    pass


class MultiplyObjectsReturned(BaseORMException):
    default_message = 'Multiply objects returned, expected exactly one'

    def __init__(self, message=None, **kwargs):
        if not message:
            message = self.default_message
        super().__init__(message, *kwargs)


class FieldError(BaseORMException):
    pass


class NoValuesFetched(BaseORMException):
    pass


class OperationalError(BaseORMException):
    pass


class ConfigurationError(Exception):
    pass


class IntegrityError(Exception):
    pass
