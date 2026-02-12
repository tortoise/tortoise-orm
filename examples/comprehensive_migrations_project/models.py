"""
ERP (Enterprise Resource Planning) Models for Comprehensive Migrations Example.

This module demonstrates all Tortoise ORM field types through a realistic ERP scenario.
Models evolve through multiple migration phases showing Create, Alter, and Drop operations.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum, IntEnum

from tortoise import fields, models
from tortoise.fields import Now, SqlDefault


class OrderStatus(IntEnum):
    """Order processing status - demonstrates IntEnumField."""

    PENDING = 1
    PROCESSING = 2
    SHIPPED = 3
    DELIVERED = 4
    CANCELLED = 5


class PaymentMethod(str, Enum):
    """Payment method types - demonstrates CharEnumField."""

    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class Company(models.Model):
    """Company entity - represents an organization."""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=300)
    company_code = fields.CharField(max_length=50, unique=True)
    description = fields.TextField()
    is_active = fields.BooleanField(default=True)
    founded_date = fields.DateField()
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.company_code})"


class Department(models.Model):
    """Department entity - organizational unit within a company."""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=150)
    company: fields.ForeignKeyRelation[Company] = fields.ForeignKeyField(
        "erp.Company", related_name="departments"
    )
    parent: fields.ForeignKeyNullableRelation[Department] = fields.ForeignKeyField(
        "erp.Department", related_name="subdepartments", null=True, db_index=True
    )
    is_active = fields.BooleanField(default=True)
    opening_time = fields.TimeField(null=True)
    closing_time = fields.TimeField(null=True)
    budget = fields.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    def __str__(self) -> str:
        return self.name


class Employee(models.Model):
    """Employee entity - person working for the company."""

    id = fields.IntField(pk=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=255, unique=True)
    department: fields.ForeignKeyRelation[Department] = fields.ForeignKeyField(
        "erp.Department", related_name="employees"
    )
    joined_date = fields.DateField()
    is_active = fields.BooleanField(default=True)
    full_name = fields.CharField(max_length=255)  # Populated via data migration, now required

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Category(models.Model):
    """Category entity - hierarchical product categorization."""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    parent: fields.ForeignKeyNullableRelation[Category] = fields.ForeignKeyField(
        "erp.Category", related_name="subcategories", null=True
    )
    priority = fields.IntField(default=0)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """Product entity - items offered by the company."""

    id = fields.IntField(pk=True)
    product_code = fields.CharField(max_length=50, unique=True)
    name = fields.CharField(max_length=200)
    description = fields.TextField()
    category: fields.ForeignKeyRelation[Category] = fields.ForeignKeyField(
        "erp.Category", related_name="products"
    )
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    external_id = fields.UUIDField(null=True)
    metadata: dict | None = fields.JSONField(null=True)
    rating = fields.FloatField(null=True, description="Average customer rating 0.0-5.0")
    processing_time = fields.TimeDeltaField(null=True, description="Average time to fulfill")
    is_active = fields.BooleanField(default=True)
    stock_quantity = fields.IntField(db_default=10)
    tracking_id = fields.CharField(
        max_length=36,
        null=True,
        db_default=SqlDefault("(lower(hex(randomblob(16))))"),
    )
    created_at = fields.DatetimeField(db_default=Now())

    def __str__(self) -> str:
        return f"{self.product_code}: {self.name}"


class Order(models.Model):
    """Order entity - customer orders demonstrating M2M and enum fields."""

    id = fields.IntField(pk=True)
    order_number = fields.CharField(max_length=50, unique=True)
    customer_email = fields.CharField(max_length=255)
    total_cents = fields.BigIntField()  # Amount in cents to avoid float precision
    total_amount = fields.DecimalField(
        max_digits=10, decimal_places=2
    )  # Populated from total_cents via data migration, now required
    status = fields.IntEnumField(OrderStatus, default=OrderStatus.PENDING)
    payment_method = fields.CharEnumField(PaymentMethod)
    products: fields.ManyToManyRelation[Product] = fields.ManyToManyField(
        "erp.Product", related_name="orders"
    )
    digital_signature = fields.BinaryField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Order {self.order_number}"


class EmployeeProfile(models.Model):
    """Employee profile - demonstrates OneToOneField."""

    id = fields.IntField(pk=True)
    employee: fields.OneToOneRelation[Employee] = fields.OneToOneField(
        "erp.Employee", related_name="profile", on_delete=fields.CASCADE
    )
    bio = fields.TextField(null=True)
    avatar_hash = fields.BinaryField(null=True)
    settings: dict | None = fields.JSONField(null=True)

    def __str__(self) -> str:
        return f"Profile for {self.employee_id}"  # type: ignore[attr-defined]


class Warehouse(models.Model):
    """Warehouse entity - storage location for inventory."""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    location = fields.CharField(max_length=300)
    is_active = fields.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Alert(models.Model):
    """Inventory alert - references Warehouse via FK.

    'Alert' < 'Warehouse' alphabetically, so the autodetector will generate
    CreateModel(Alert) before CreateModel(Warehouse), exercising the fix for
    LookupError in CreateModel.state_forward with forward FK references.
    """

    id = fields.IntField(pk=True)
    warehouse: fields.ForeignKeyRelation[Warehouse] = fields.ForeignKeyField(
        "erp.Warehouse", related_name="alerts"
    )
    message = fields.TextField()
    is_resolved = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Alert: {self.message[:50]}"
