from tortoise.fields import Field


class Parameter:
    __slots__ = ("name", "model", "value_encoder", "field_object",)

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = None
        self.value_encoder = None
        self.field_object: Field | None = None

    def encode_value(self, value: ...) -> ...:
        if self.value_encoder:
            if self.field_object is not None:
                return self.value_encoder(value, self.model, self.field_object)
            return self.value_encoder(value, self.model)
        if self.field_object is not None:
            return self.field_object.to_db_value(value, self.model)
        return self.value_encoder