from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from ..accounts.models import User
    from ..orders.models import Order


class Product(models.Model):
    id = fields.IntField(primary_key=True)
    sku = fields.CharField(max_length=32, unique=True)
    name = fields.CharField(max_length=150)
    price_cents = fields.IntField()
    owner: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "accounts.User",
        related_name="owned_products",
        null=True,
    )
    last_order: fields.ForeignKeyNullableRelation[Order] = fields.ForeignKeyField(
        "orders.Order",
        related_name="last_order_products",
        null=True,
    )

    class Meta:
        table = "catalog_product"
