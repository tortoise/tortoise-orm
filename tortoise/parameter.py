from typing import Self

from tortoise.fields import Field
from pypika_tortoise import SqlContext


class Parameter:
    __slots__ = ("name", "model", "value_encoder", "field_object", "encode",)

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = None
        self.value_encoder = None
        self.field_object: Field | None = None
        self.encode = None

    def clone(self) -> Self:
        new = self.__new__(self.__class__)
        new.name = self.name
        new.model = self.model
        new.value_encoder = self.value_encoder
        new.field_object = self.field_object
        new.encode = self.encode

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


class CollectionParameter(Parameter):
    __slots__ = ("collection_size", "collection_encoder",)

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.collection_size = None
        self.collection_encoder = None

    @classmethod
    def from_simple_param(cls, param: Parameter) -> Self:
        new_param = cls(param.name)
        new_param.model = param.model
        new_param.value_encoder = param.value_encoder
        new_param.field_object = param.field_object
        new_param.encode = param.encode
        return new_param

    def encode_collection(self, value: ...) -> ...:
        if self.field_object is not None:
            return self.collection_encoder(value, self.model, self.field_object)
        else:
            return self.collection_encoder(value, self.model)

    def get_sql(self, ctx: SqlContext) -> str:
        if self.collection_size is None:
            if ctx.parameterizer is not None:
                ctx.parameterizer.create_param(self)
            return "?"
        else:
            if ctx.parameterizer is not None:
                for idx in range(self.collection_size):
                    new_param = self.clone()
                    new_param.collection_encoder = new_param.value_encoder
                    new_param.value_encoder = None
                    ctx.parameterizer.create_param(new_param)
            return f"({','.join(['?' for _ in range(self.collection_size)])})"