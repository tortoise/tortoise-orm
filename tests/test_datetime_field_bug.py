"""Test coverage for DatetimeField auto_now and auto_now_add bug fix."""

import pytest

from tortoise import fields
from tortoise.exceptions import ConfigurationError


def test_datetimefield_auto_now_only():
    """Test DatetimeField with only auto_now=True."""
    field = fields.DatetimeField(auto_now=True)
    assert field.auto_now is True
    assert field.auto_now_add is False

    # Verify describe() returns correct values
    desc = field.describe(serializable=True)
    assert desc["auto_now"] is True
    assert desc["auto_now_add"] is False


def test_datetimefield_auto_now_add_only():
    """Test DatetimeField with only auto_now_add=True."""
    field = fields.DatetimeField(auto_now_add=True)
    assert field.auto_now is False
    assert field.auto_now_add is True

    # Verify describe() returns correct values
    desc = field.describe(serializable=True)
    assert desc["auto_now"] is False
    assert desc["auto_now_add"] is True


def test_datetimefield_both_flags_raises():
    """Test DatetimeField raises when both auto_now and auto_now_add are True."""
    with pytest.raises(
        ConfigurationError, match="You can choose only 'auto_now' or 'auto_now_add'"
    ):
        fields.DatetimeField(auto_now=True, auto_now_add=True)


def test_datetimefield_neither_flag():
    """Test DatetimeField with neither flag set."""
    field = fields.DatetimeField()
    assert field.auto_now is False
    assert field.auto_now_add is False

    desc = field.describe(serializable=True)
    assert desc["auto_now"] is False
    assert desc["auto_now_add"] is False


def test_datetimefield_constraints_auto_now():
    """Test that auto_now sets readOnly constraint."""
    field = fields.DatetimeField(auto_now=True)
    constraints = field.constraints
    assert constraints.get("readOnly") is True


def test_datetimefield_constraints_auto_now_add():
    """Test that auto_now_add sets readOnly constraint."""
    field = fields.DatetimeField(auto_now_add=True)
    constraints = field.constraints
    assert constraints.get("readOnly") is True


def test_datetimefield_constraints_neither():
    """Test that neither flag sets no readOnly constraint."""
    field = fields.DatetimeField()
    constraints = field.constraints
    assert "readOnly" not in constraints


def test_timefield_auto_now_only():
    """Test TimeField with only auto_now=True."""
    field = fields.TimeField(auto_now=True)
    assert field.auto_now is True
    assert field.auto_now_add is False


def test_timefield_auto_now_add_only():
    """Test TimeField with only auto_now_add=True."""
    field = fields.TimeField(auto_now_add=True)
    assert field.auto_now is False
    assert field.auto_now_add is True


def test_timefield_both_flags_raises():
    """Test TimeField raises when both auto_now and auto_now_add are True."""
    with pytest.raises(
        ConfigurationError, match="You can choose only 'auto_now' or 'auto_now_add'"
    ):
        fields.TimeField(auto_now=True, auto_now_add=True)
