from tortoise.fields import Field


class TSVectorField(Field):
    SQL_TYPE = "TSVECTOR"
