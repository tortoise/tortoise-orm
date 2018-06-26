from tortoise.fields import Field


class JSONField(Field):
    def __init__(self, encoder=None, decoder=None, *args, **kwargs):
        super().__init__(dict, *args, **kwargs)
        if encoder is None:
            from json import dumps
            self.encoder = dumps
        else:
            self.encoder = encoder

        if decoder is None:
            from json import loads
            self.decoder = loads
        else:
            self.decoder = decoder

    def to_db_value(self, value):
        if value is None:
            return value
        return self.encoder(value)

    def to_python_value(self, value):
        if value is None:
            return value
        return self.decoder(value)
