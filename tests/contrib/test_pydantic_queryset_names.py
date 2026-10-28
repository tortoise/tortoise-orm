import pytest

from tests.testmodels import Event, Tournament
from tortoise.contrib.pydantic import pydantic_queryset_creator


def test_separate_list_and_item_schema_names():
    model = pydantic_queryset_creator(
        Tournament, name="Tournaments", submodel_name="TournamentItem", include=("id", "name")
    )
    schema = model.model_json_schema()

    assert model.__name__ == "Tournaments"
    assert schema["title"] == "Tournaments"
    assert schema["items"] == {"$ref": "#/$defs/TournamentItem"}
    assert schema["$defs"]["TournamentItem"]["title"] == "TournamentItem"
    assert set(schema["$defs"]["TournamentItem"]["properties"]) == {"id", "name"}
    assert model.model_validate([{"id": 1, "name": "Final"}]).model_dump() == [
        {"id": 1, "name": "Final"}
    ]


def test_item_name_also_defines_the_generated_list_name():
    model = pydantic_queryset_creator(
        Tournament, submodel_name="TournamentEntry", include=("id", "name")
    )
    schema = model.model_json_schema()

    assert model.__name__ == "TournamentEntry_list"
    assert schema["title"] == "TournamentEntry_list"
    assert schema["items"] == {"$ref": "#/$defs/TournamentEntry"}


@pytest.mark.parametrize("name", [None, "LegacyTournamentList"])
def test_existing_queryset_names_remain_unchanged(name):
    model = pydantic_queryset_creator(Tournament, name=name, include=("id", "name"))
    schema = model.model_json_schema()
    item_schema = next(iter(schema["$defs"].values()))

    assert schema["title"] == (name or "Tournament_list")
    assert item_schema["title"] == (name or "Tournament")


def test_item_name_preserves_field_selection():
    model = pydantic_queryset_creator(
        Tournament,
        name="TournamentNames",
        submodel_name="TournamentName",
        include=("id", "name"),
        exclude=("id",),
    )
    schema = model.model_json_schema()

    assert set(schema["$defs"]["TournamentName"]["properties"]) == {"name"}
    assert model.model_validate([{"name": "Final"}]).model_dump() == [{"name": "Final"}]


def test_differently_named_items_keep_their_own_schema():
    models = [
        pydantic_queryset_creator(
            Tournament, name="TournamentResults", submodel_name=name, include=("id", "name")
        )
        for name in ("FirstTournament", "SecondTournament", "FirstTournament")
    ]

    for model, name in zip(models, ("FirstTournament", "SecondTournament", "FirstTournament")):
        schema = model.model_json_schema()
        assert schema["items"] == {"$ref": f"#/$defs/{name}"}
        assert schema["$defs"][name]["title"] == name


@pytest.mark.asyncio
async def test_named_items_serialize_a_queryset(db):
    tournament = await Tournament.create(name="Final")
    model = pydantic_queryset_creator(
        Tournament, name="TournamentPage", submodel_name="TournamentResult", include=("id", "name")
    )

    result = await model.from_queryset(Tournament.filter(id=tournament.id))

    assert result.model_dump() == [{"id": tournament.id, "name": "Final"}]
    assert result.root[0].__class__.__name__ == "TournamentResult"


@pytest.mark.asyncio
async def test_named_items_prefetch_related_models(db):
    tournament = await Tournament.create(name="Final")
    event = await Event.create(name="Match", tournament=tournament)
    model = pydantic_queryset_creator(
        Event,
        name="Events",
        submodel_name="EventItem",
        include=("event_id", "name", "tournament", "tournament.id", "tournament.name"),
    )

    result = await model.from_queryset(Event.filter(event_id=event.event_id))

    assert result.model_dump() == [
        {
            "event_id": event.event_id,
            "name": "Match",
            "tournament": {"id": tournament.id, "name": "Final"},
        }
    ]
    assert model.model_json_schema()["items"] == {"$ref": "#/$defs/EventItem"}
