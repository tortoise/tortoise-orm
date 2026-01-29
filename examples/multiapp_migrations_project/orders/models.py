from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:
    from ..accounts.models import User
    from ..catalog.models import Product


class Order(models.Model):
    id = fields.IntField(primary_key=True)
    number = fields.CharField(max_length=40, unique=True)
    status = fields.CharField(max_length=20)
    user: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "accounts.User",
        related_name="orders",
        null=True,
    )
    approved_by: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "accounts.User",
        related_name="approved_orders",
        null=True,
    )

    class Meta:
        table = "orders_order"


class OrderItem(models.Model):
    id = fields.IntField(primary_key=True)
    order: fields.ForeignKeyRelation[Order] = fields.ForeignKeyField(
        "orders.Order",
        related_name="items",
    )
    product: fields.ForeignKeyNullableRelation[Product] = fields.ForeignKeyField(
        "catalog.Product",
        related_name="order_items",
        null=True,
    )
    quantity = fields.IntField()

    class Meta:
        table = "orders_order_item"
