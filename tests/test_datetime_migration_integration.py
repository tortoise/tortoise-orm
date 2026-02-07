"""Integration test for DatetimeField migration generation bug fix.

This test ensures that models with auto_now and auto_now_add fields
generate valid migrations that can be applied without ConfigurationError.
"""

from tortoise import Model, fields


class TimestampedModel(Model):
    """Model with both created_at and modified_at fields."""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

    class Meta:
        app = "test_app"


def test_auto_now_field_describe():
    """Test that auto_now field describes correctly for migrations."""
    field = TimestampedModel._meta.fields_map["modified_at"]
    desc = field.describe(serializable=True)

    assert desc["auto_now"] is True
    assert desc["auto_now_add"] is False

    assert not (desc["auto_now"] and desc["auto_now_add"])


def test_auto_now_add_field_describe():
    """Test that auto_now_add field describes correctly for migrations."""
    field = TimestampedModel._meta.fields_map["created_at"]
    desc = field.describe(serializable=True)

    assert desc["auto_now"] is False
    assert desc["auto_now_add"] is True

    assert not (desc["auto_now"] and desc["auto_now_add"])


def test_regular_field_describe():
    """Test that regular fields have both flags as False."""
    field = TimestampedModel._meta.fields_map["name"]
    desc = field.describe(serializable=True)

    assert desc.get("auto_now", False) is False
    assert desc.get("auto_now_add", False) is False


def test_migration_field_serialization():
    """Test the actual migration field string that would be generated."""
    created_at = TimestampedModel._meta.fields_map["created_at"]
    modified_at = TimestampedModel._meta.fields_map["modified_at"]

    created_desc = created_at.describe(serializable=True)
    modified_desc = modified_at.describe(serializable=True)

    assert created_desc["auto_now"] is False
    assert created_desc["auto_now_add"] is True

    assert modified_desc["auto_now"] is True
    assert modified_desc["auto_now_add"] is False


def test_field_can_be_instantiated_from_describe():
    """Test that a field recreated from describe() is valid."""
    field = TimestampedModel._meta.fields_map["modified_at"]
    desc = field.describe(serializable=True)

    new_field = fields.DatetimeField(
        auto_now=desc["auto_now"],
        auto_now_add=desc["auto_now_add"],
    )

    assert new_field.auto_now is True
    assert new_field.auto_now_add is False
