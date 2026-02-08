from tortoise.fields import Field
from pypika_tortoise import SqlContext


class Parameter:
    __slots__ = ("name", "model", "value_encoder", "field_object", "encode", "container_size",)

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = None
        self.value_encoder = None
        self.field_object: Field | None = None
        self.encode = None
        self.container_size = None

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

    def get_sql(self, ctx: SqlContext) -> str:
        if self.container_size is None:
            if ctx.parameterizer is not None:
                ctx.parameterizer.create_param(self)
            return "?"
        else:
            if ctx.parameterizer is not None:
                ctx.parameterizer.create_param(self)
            return f"({','.join(['?' for _ in range(self.container_size)])})"