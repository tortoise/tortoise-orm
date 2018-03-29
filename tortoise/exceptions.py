class BaseORMException(Exception):
    pass


class MultiplyObjectsReturned(BaseORMException):
    default_message = 'Multiply objects returned, expected exactly one'

    def __init__(self, message=None, *args, **kwargs):
        if not message:
            message = self.default_message
        super().__init__(message, *args)


class UnknownFilterParameter(BaseORMException):
    pass


class NoValuesFetched(BaseORMException):
    pass
