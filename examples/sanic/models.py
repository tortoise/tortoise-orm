from typing import Dict, Union

from tortoise import Model, fields


class User(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50)

    def to_json(self) -> Dict[str, Union[int, str]]:
        return {f: getattr(self, f) for f in self._meta.fields}

    def __str__(self):
        return f"User {self.id}: {self.name}"
