from tortoise import fields, models


class Team(models.Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "accounts_team"


class User(models.Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=200, unique=True)
    team: fields.ForeignKeyNullableRelation[Team] = fields.ForeignKeyField(
        "accounts.Team",
        related_name="members",
        null=True,
    )
    favorite_product: fields.ForeignKeyNullableRelation["Product"] = fields.ForeignKeyField(
        "catalog.Product",
        related_name="fans",
        null=True,
    )
    last_order: fields.ForeignKeyNullableRelation["Order"] = fields.ForeignKeyField(
        "orders.Order",
        related_name="customers_last_order",
        null=True,
    )

    class Meta:
        table = "accounts_user"
