class TortoiseMigrationError(Exception):
    pass


class IncompatibleStateError(TortoiseMigrationError):
    """
    Raised when TortoiseOperation can't be executed on given State object
    """