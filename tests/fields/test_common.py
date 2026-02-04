import pytest

from tortoise import fields


# Tests for field.required property - no database access needed
@pytest.mark.asyncio
async def test_required_by_default():
    assert fields.Field().required is True


@pytest.mark.asyncio
async def test_if_generated_then_not_required():
    assert fields.Field(generated=True).required is False


@pytest.mark.asyncio
async def test_if_null_then_not_required():
    assert fields.Field(null=True).required is False


@pytest.mark.asyncio
async def test_if_has_non_null_default_then_not_required():
    assert fields.TextField(default="").required is False


@pytest.mark.asyncio
async def test_if_null_default_then_required():
    assert fields.TextField(default=None).required is True
