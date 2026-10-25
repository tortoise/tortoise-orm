from collections.abc import Callable, Iterable

import pytest

from tests.testmodels import Tournament
from tortoise.exceptions import FieldError, OperationalError

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("db")]

FieldFactory = Callable[[tuple[str, ...]], Iterable[str]]


@pytest.fixture(params=["list", "tuple", "iterator", "generator"])
def field_factory(request: pytest.FixtureRequest) -> FieldFactory:
    factories: dict[str, FieldFactory] = {
        "list": list,
        "tuple": tuple,
        "iterator": iter,
        "generator": lambda names: (name for name in names),
    }
    return factories[request.param]


async def test_selected_fields_are_refreshed(field_factory: FieldFactory) -> None:
    obj = await Tournament.create(name="before", desc="local description")
    await Tournament.filter(pk=obj.pk).update(name="after", desc="database description")

    await obj.refresh_from_db(fields=field_factory(("name",)))

    assert obj.name == "after"
    assert obj.desc == "local description"


async def test_multiple_fields_are_refreshed(field_factory: FieldFactory) -> None:
    obj = await Tournament.create(name="before", desc="local description")
    await Tournament.filter(pk=obj.pk).update(name="after", desc="database description")

    await obj.refresh_from_db(fields=field_factory(("desc", "name")))

    assert obj.name == "after"
    assert obj.desc == "database description"


async def test_empty_fields_refresh_all_fields(field_factory: FieldFactory) -> None:
    obj = await Tournament.create(name="before", desc="local description")
    await Tournament.filter(pk=obj.pk).update(name="after", desc="database description")

    await obj.refresh_from_db(fields=field_factory(()))

    assert obj.name == "after"
    assert obj.desc == "database description"


async def test_invalid_fields_keep_instance_values(field_factory: FieldFactory) -> None:
    obj = await Tournament.create(name="before", desc="local description")
    await Tournament.filter(pk=obj.pk).update(name="after", desc="database description")

    with pytest.raises(FieldError):
        await obj.refresh_from_db(fields=field_factory(("missing_field",)))

    assert obj.name == "before"
    assert obj.desc == "local description"


async def test_unpersisted_instance_does_not_consume_fields() -> None:
    obj = Tournament(name="unpersisted")
    consumed: list[str] = []

    def field_names() -> Iterable[str]:
        consumed.append("name")
        yield "name"

    with pytest.raises(OperationalError, match="Can't refresh unpersisted record"):
        await obj.refresh_from_db(fields=field_names())

    assert consumed == []
