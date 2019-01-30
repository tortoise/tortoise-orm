from typing import List


class ValidationError(Exception):

    def __init__(self, errors: List[str]):
        super().__init__()
        self.errors = errors
