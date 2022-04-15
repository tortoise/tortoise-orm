from typing import Any


class Condition:
    def __init__(self, value: Any):
        self.value = value


class NotEQ(Condition):
    def __eq__(self, other: Any):
        return self.value != other


class In(Condition):
    def __init__(self, *args: Any):
        super(In, self).__init__(args)

    def __eq__(self, other: Any):
        return other in self.value


class NotIn(Condition):
    def __init__(self, *args: Any):
        super(NotIn, self).__init__(args)

    def __eq__(self, other: Any):
        return other not in self.value
