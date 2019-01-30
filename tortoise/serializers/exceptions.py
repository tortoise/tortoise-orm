from typing import List


class ValidationError(Exception):
    """Raised when inbound data has failed validation."""

    def __init__(self, errors: List[str]):
        super().__init__()
        self.errors = errors


class MissingDependencies(Exception):
    """Raised when one or more of a backend's dependencies are not installed."""

    def __init__(self, *dependencies: str):
        super().__init__()
        self.dependencies = dependencies
