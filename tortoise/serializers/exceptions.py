class ValidationError(Exception):

    def __init__(self, errors):
        super().__init__()
        self.errors = errors
