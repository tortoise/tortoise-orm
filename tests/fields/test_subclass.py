import pytest

from tests.fields.subclass_models import (
    Contact,
    ContactTypeEnum,
    RaceParticipant,
    RacePlacingEnum,
)


async def create_participants():
    """Helper to create race participants for tests."""
    test1 = await RaceParticipant.create(
        first_name="Alex",
        place=RacePlacingEnum.FIRST,
        predicted_place=RacePlacingEnum.THIRD,
    )
    test2 = await RaceParticipant.create(
        first_name="Ben",
        place=RacePlacingEnum.SECOND,
        predicted_place=RacePlacingEnum.FIRST,
    )
    test3 = await RaceParticipant.create(first_name="Chris", place=RacePlacingEnum.THIRD)
    test4 = await RaceParticipant.create(first_name="Bill")

    return test1, test2, test3, test4


@pytest.mark.asyncio
async def test_enum_field_create(db_subclass_fields):
    """Asserts that the new field is saved properly."""
    test1, _, _, _ = await create_participants()
    assert test1 in await RaceParticipant.all()
    assert test1.place == RacePlacingEnum.FIRST


@pytest.mark.asyncio
async def test_enum_field_update(db_subclass_fields):
    """Asserts that the new field can be updated correctly."""
    test1, _, _, _ = await create_participants()
    test1.place = RacePlacingEnum.SECOND
    await test1.save()

    tied_second = await RaceParticipant.filter(place=RacePlacingEnum.SECOND)

    assert test1 in tied_second
    assert len(tied_second) == 2


@pytest.mark.asyncio
async def test_enum_field_filter(db_subclass_fields):
    """Assert that filters correctly select the enums."""
    await create_participants()

    first_place = await RaceParticipant.filter(place=RacePlacingEnum.FIRST).first()
    second_place = await RaceParticipant.filter(place=RacePlacingEnum.SECOND).first()

    assert first_place.place == RacePlacingEnum.FIRST
    assert second_place.place == RacePlacingEnum.SECOND


@pytest.mark.asyncio
async def test_enum_field_delete(db_subclass_fields):
    """Assert that delete correctly removes the right participant by their place."""
    await create_participants()
    await RaceParticipant.filter(place=RacePlacingEnum.FIRST).delete()
    assert await RaceParticipant.all().count() == 3


@pytest.mark.asyncio
async def test_enum_field_default(db_subclass_fields):
    """Test that default enum value is applied correctly."""
    _, _, _, test4 = await create_participants()
    assert test4.place == RacePlacingEnum.DNF


@pytest.mark.asyncio
async def test_enum_field_null(db_subclass_fields):
    """Assert that filtering by None selects the records which are null."""
    _, _, test3, test4 = await create_participants()

    no_predictions = await RaceParticipant.filter(predicted_place__isnull=True)

    assert test3 in no_predictions
    assert test4 in no_predictions


@pytest.mark.asyncio
async def test_update_with_int_enum_value(db_subclass_fields):
    """Test updating with integer enum value."""
    contact = await Contact.create()
    contact.type = ContactTypeEnum.home
    await contact.save()


@pytest.mark.asyncio
async def test_exception_on_invalid_data_type_in_int_field(db_subclass_fields):
    """Test that invalid data types raise appropriate exceptions."""
    contact = await Contact.create()

    contact.type = "not_int"
    with pytest.raises((TypeError, ValueError)):
        await contact.save()
