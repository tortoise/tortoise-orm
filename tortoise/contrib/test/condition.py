from typing import Any


class Condition:
    def __init__(self, value: Any) -> None:
        self.value = value


class NotEQ(Condition):
    def __eq__(self, other: Any) -> bool:
        return self.value != other

    def __str__(self) -> str:
        return f"<!={self.value}>"


class In(Condition):
    def __init__(self, *args: Any) -> None:
        super().__init__(args)

    def __eq__(self, other: Any) -> bool:
        return other in self.value

    def __str__(self) -> str:
        return f"<in {self.value}>"


class NotIn(Condition):
    def __init__(self, *args: Any) -> None:
        super().__init__(args)

    def __eq__(self, other: Any) -> bool:
        return other not in self.value

    def __str__(self) -> str:
        return f"<not in {self.value}>"
