import pytest

from tests.testmodels import (
    Tournament,
    UniqueTogetherFields,
    UniqueTogetherFieldsWithFK,
)
from tortoise.exceptions import IntegrityError


@pytest.mark.asyncio
async def test_unique_together(db):
    first_name = "first_name"
    last_name = "last_name"

    await UniqueTogetherFields.create(first_name=first_name, last_name=last_name)

    with pytest.raises(IntegrityError):
        await UniqueTogetherFields.create(first_name=first_name, last_name=last_name)


@pytest.mark.asyncio
async def test_unique_together_with_foreign_keys(db):
    tournament_name = "tournament_name"
    text = "text"

    tournament = await Tournament.create(name=tournament_name)

    await UniqueTogetherFieldsWithFK.create(text=text, tournament=tournament)

    with pytest.raises(IntegrityError):
        await UniqueTogetherFieldsWithFK.create(text=text, tournament=tournament)
