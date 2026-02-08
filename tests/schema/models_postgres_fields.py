from tortoise import Model
from tortoise.contrib.postgres.fields import ArrayField, TSVectorField


class PostgresFields(Model):
    tsvector = TSVectorField()
    text_array = ArrayField(element_type="text", default=["a", "b", "c"])
    varchar_array = ArrayField(element_type="varchar(32)", default=["aa", "bbb", "cccc"])
    int_array = ArrayField(element_type="int", default=[1, 2, 3], null=True)
    real_array = ArrayField(
        element_type="real",
        default=[1.1, 2.2, 3.3],
        description="this is array of real numbers",
    )

    class Meta:
        table = "postgres_fields"
