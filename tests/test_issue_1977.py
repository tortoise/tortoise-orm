"""Test for issue #1977 - pydantic_model_creator incorrectly marks fields as Optional."""
import pytest
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class ModelWithDefaultField(Model):
    """Model with a field that has a default value but is not nullable."""

    id = fields.IntField(pk=True)
    altitude = fields.FloatField(default=0, null=False)
    name = fields.CharField(max_length=50)

    class Meta:
        app = "models"
        table = "model_with_default_field"


@pytest.mark.asyncio
async def test_pydantic_model_with_default_not_optional(db):
    """Test that fields with default values but null=False are not marked as Optional."""
    # Create Pydantic schema
    Schema = pydantic_model_creator(
        ModelWithDefaultField,
        name="ModelWithDefaultFieldSchema",
    )

    # Check the field annotations
    field_info = Schema.model_fields["altitude"]

    # The field should NOT be Optional (Union with None)
    # It should just be float since it's not nullable
    annotation = field_info.annotation

    # Get the origin and args to check if it's Optional
    import typing
    if hasattr(typing, 'get_origin'):
        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)
    else:
        origin = getattr(annotation, '__origin__', None)
        args = getattr(annotation, '__args__', ())

    # If it's a Union type with NoneType, it's Optional
    is_optional = (
        origin is typing.Union and
        type(None) in args
    )

    # This should NOT be optional - the bug makes it optional
    assert not is_optional, (
        f"Field 'altitude' should not be Optional. "
        f"It has default=0 and null=False, so None should not be accepted. "
        f"Got annotation: {annotation}"
    )

    # Test that validation rejects None
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Schema(id=1, altitude=None, name="test")

    # Should fail on altitude field
    assert "altitude" in str(exc_info.value)
