from typing import Self

from tortoise.fields import Field
from pypika_tortoise import SqlContext


class Parameter:
    __slots__ = ("name", "model", "value_encoder", "field_object", "encode", "container_size", "container_encoder",)

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = None
        self.value_encoder = None
        self.container_encoder = None
        self.field_object: Field | None = None
        self.encode = None
        self.container_size = None

    def clone(self) -> Self:
        new = self.__new__(self.__class__)
        new.name = self.name
        new.model = self.model
        new.container_encoder = self.container_encoder
        new.value_encoder = self.value_encoder
        new.field_object = self.field_object
        new.encode = self.encode
        new.container_size = self.container_size

        return new

    def encode_value(self, value: ...) -> ...:
        encoded = value

        if self.value_encoder:
            if self.field_object is not None:
                encoded = self.value_encoder(value, self.model, self.field_object)
            else:
                encoded = self.value_encoder(value, self.model)
        elif self.field_object is not None:
            encoded = self.field_object.to_db_value(value, self.model)

        if self.encode:
            encoded = self.encode(encoded)

        return encoded

    def encode_container(self, value: ...) -> ...:
        if self.field_object is not None:
            return self.container_encoder(value, self.model, self.field_object)
        else:
            return self.container_encoder(value, self.model)

    def get_sql(self, ctx: SqlContext) -> str:
        if self.container_size is None:
            if ctx.parameterizer is not None:
                ctx.parameterizer.create_param(self)
            return "?"
        else:
            if ctx.parameterizer is not None:
                for idx in range(self.container_size):
                    new_param = self.clone()
                    new_param.name += f"[{idx}]"
                    new_param.container_encoder = new_param.value_encoder
                    new_param.value_encoder = None
                    ctx.parameterizer.create_param(new_param)
            return f"({','.join(['?' for _ in range(self.container_size)])})"