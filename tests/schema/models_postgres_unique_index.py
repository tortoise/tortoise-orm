from tortoise import Model, fields

from tortoise.contrib.postgres.indexes import PostgreSQLIndex


class Customer(Model):
    shop_id = fields.IntField()
    phone_number = fields.CharField(max_length=20)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        indexes = [
            PostgreSQLIndex(
                fields=("shop_id", "phone_number", "deleted_at"),
                unique=True,
                nulls_not_distinct=True,
            ),
        ]
