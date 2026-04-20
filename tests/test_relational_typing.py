from typing_extensions import assert_type

from tests.testmodels import Address, Event, Reporter, Tournament
from tortoise import fields
from tortoise.models import Model


def test_foreign_key_field_type_inference() -> None:
    field = fields.ForeignKeyField(Tournament, related_name="events")

    assert_type(field, fields.ForeignKeyRelation[Tournament])


def test_nullable_foreign_key_field_type_inference() -> None:
    field = fields.ForeignKeyField(Reporter, related_name="events", null=True)

    assert_type(field, fields.ForeignKeyNullableRelation[Reporter])


def test_foreign_key_field_string_target_is_backward_compatible() -> None:
    field = fields.ForeignKeyField("models.Tournament", related_name="events")

    assert_type(field, fields.ForeignKeyRelation[Model])


def test_nullable_foreign_key_field_string_target_is_backward_compatible() -> None:
    field = fields.ForeignKeyField("models.Reporter", related_name="events", null=True)

    assert_type(field, fields.ForeignKeyNullableRelation[Model])


def test_one_to_one_field_type_inference() -> None:
    field = fields.OneToOneField(Event, related_name="address", on_delete=fields.CASCADE)

    assert_type(field, fields.OneToOneRelation[Event])


def test_nullable_one_to_one_field_type_inference() -> None:
    field = fields.OneToOneField(
        Event,
        related_name="address_null",
        on_delete=fields.CASCADE,
        null=True,
    )

    assert_type(field, fields.OneToOneNullableRelation[Event])


def test_one_to_one_field_string_target_is_backward_compatible() -> None:
    field = fields.OneToOneField(
        "models.Event",
        related_name="address",
        on_delete=fields.CASCADE,
    )

    assert_type(field, fields.OneToOneRelation[Model])


def test_nullable_one_to_one_field_string_target_is_backward_compatible() -> None:
    field = fields.OneToOneField(
        "models.Event",
        related_name="address_null",
        on_delete=fields.CASCADE,
        null=True,
    )

    assert_type(field, fields.OneToOneNullableRelation[Model])


def test_many_to_many_field_type_inference() -> None:
    field = fields.ManyToManyField(Address, related_name="events")

    assert_type(field, fields.ManyToManyRelation[Address])


def test_many_to_many_field_string_target_is_backward_compatible() -> None:
    field = fields.ManyToManyField("models.Address", related_name="events")

    assert_type(field, fields.ManyToManyRelation[Model])
