class TortoiseMigrationError(Exception):
    """Base migration error."""


class IncompatibleStateError(TortoiseMigrationError):
    """Raised when a migration operation can't be executed on a given State."""
