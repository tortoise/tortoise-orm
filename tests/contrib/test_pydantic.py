import copy

import pytest
import pytest_asyncio
from pydantic import ConfigDict, ValidationError

from tests.testmodels import (
    Address,
    CamelCaseAliasPerson,
    Employee,
    EnumFields,
    Event,
    IntFields,
    JSONFields,
    ModelTestPydanticMetaBackwardRelations1,
    ModelTestPydanticMetaBackwardRelations2,
    Reporter,
    Team,
    Tournament,
    User,
    json_pydantic_default,
)
from tortoise.contrib.pydantic import (
    PydanticModel,
    pydantic_model_creator,
    pydantic_queryset_creator,
)


# Fixtures for TestPydantic
@pytest_asyncio.fixture
async def pydantic_setup(db):
    """Setup for pydantic tests with models and data."""
    Event_Pydantic = pydantic_model_creator(Event)
    Event_Pydantic_List = pydantic_queryset_creator(Event)
    Tournament_Pydantic = pydantic_model_creator(Tournament)
    Team_Pydantic = pydantic_model_creator(Team)
    Address_Pydantic = pydantic_model_creator(Address)
    ModelTestPydanticMetaBackwardRelations1_Pydantic = pydantic_model_creator(
        ModelTestPydanticMetaBackwardRelations1
    )
    ModelTestPydanticMetaBackwardRelations2_Pydantic = pydantic_model_creator(
        ModelTestPydanticMetaBackwardRelations2
    )

    class PydanticMetaOverride:
        backward_relations = False

    Event_Pydantic_non_backward_from_override = pydantic_model_creator(
        Event, meta_override=PydanticMetaOverride, name="Event_non_backward"
    )

    tournament = await Tournament.create(name="New Tournament")
    reporter = await Reporter.create(name="The Reporter")
    event = await Event.create(name="Test", tournament=tournament, reporter=reporter)
    event2 = await Event.create(name="Test2", tournament=tournament)
    address = await Address.create(city="Santa Monica", street="Ocean", event=event)
    team1 = await Team.create(name="Onesies")
    team2 = await Team.create(name="T-Shirts")
    await event.participants.add(team1, team2)
    await event2.participants.add(team1, team2)

    return {
        "Event_Pydantic": Event_Pydantic,
        "Event_Pydantic_List": Event_Pydantic_List,
        "Tournament_Pydantic": Tournament_Pydantic,
        "Team_Pydantic": Team_Pydantic,
        "Address_Pydantic": Address_Pydantic,
        "ModelTestPydanticMetaBackwardRelations1_Pydantic": ModelTestPydanticMetaBackwardRelations1_Pydantic,
        "ModelTestPydanticMetaBackwardRelations2_Pydantic": ModelTestPydanticMetaBackwardRelations2_Pydantic,
        "Event_Pydantic_non_backward_from_override": Event_Pydantic_non_backward_from_override,
        "tournament": tournament,
        "reporter": reporter,
        "event": event,
        "event2": event2,
        "address": address,
        "team1": team1,
        "team2": team2,
    }


@pytest.mark.asyncio
async def test_backward_relations_with_meta_override(db, pydantic_setup):
    Event_Pydantic = pydantic_setup["Event_Pydantic"]
    Event_Pydantic_non_backward_from_override = pydantic_setup[
        "Event_Pydantic_non_backward_from_override"
    ]

    event_schema = copy.deepcopy(dict(Event_Pydantic.model_json_schema()))
    event_non_backward_schema_by_override = copy.deepcopy(
        dict(Event_Pydantic_non_backward_from_override.model_json_schema())
    )
    assert "address" in event_schema["properties"]
    assert "address" not in event_non_backward_schema_by_override["properties"]
    del event_schema["properties"]["address"]
    assert event_schema["properties"] == event_non_backward_schema_by_override["properties"]


@pytest.mark.asyncio
async def test_backward_relations_with_pydantic_meta(db, pydantic_setup):
    ModelTestPydanticMetaBackwardRelations1_Pydantic = pydantic_setup[
        "ModelTestPydanticMetaBackwardRelations1_Pydantic"
    ]
    ModelTestPydanticMetaBackwardRelations2_Pydantic = pydantic_setup[
        "ModelTestPydanticMetaBackwardRelations2_Pydantic"
    ]

    test_model1_schema = ModelTestPydanticMetaBackwardRelations1_Pydantic.model_json_schema()
    test_model2_schema = ModelTestPydanticMetaBackwardRelations2_Pydantic.model_json_schema()
    assert "threes" in test_model2_schema["properties"]
    assert "threes" not in test_model1_schema["properties"]
    del test_model2_schema["properties"]["threes"]
    assert test_model2_schema["properties"] == test_model1_schema["properties"]
    print(test_model2_schema)


@pytest.mark.asyncio
async def test_backward_relations_annotated_kept(db):
    """backward_relations=False should keep explicitly annotated ReverseRelation fields."""
    from tests.testmodels import ModelTestPydanticAnnotatedBackwardRel

    Pydantic = pydantic_model_creator(ModelTestPydanticAnnotatedBackwardRel)
    schema = Pydantic.model_json_schema()
    # Annotated backward relation should be included
    assert "annotated_children" in schema["properties"]
    # Unannotated backward relation should be excluded
    assert "unannotated_children" not in schema["properties"]


@pytest.mark.asyncio
async def test_event_schema(db, pydantic_setup):
    Event_Pydantic = pydantic_setup["Event_Pydantic"]
    assert Event_Pydantic.model_json_schema() == {
        "$defs": {
            "Address_zwygvk_leaf": {
                "additionalProperties": False,
                "properties": {
                    "city": {"maxLength": 64, "title": "City", "type": "string"},
                    "street": {"maxLength": 128, "title": "Street", "type": "string"},
                    "m2mwitho2opks": {
                        "items": {"$ref": "#/$defs/M2mWithO2oPk_zpacbp_leaf"},
                        "title": "M2Mwitho2Opks",
                        "type": "array",
                    },
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                },
                "required": ["city", "street", "event_id", "m2mwitho2opks"],
                "title": "Address",
                "type": "object",
            },
            "M2mWithO2oPk_zpacbp_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 64, "title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "M2mWithO2oPk",
                "type": "object",
            },
            "Reporter_ifqfo2_leaf": {
                "additionalProperties": False,
                "description": "Whom is assigned as the reporter",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "Reporter",
                "type": "object",
            },
            "Team_fcszy2_leaf": {
                "additionalProperties": False,
                "description": "Team that is a playing",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                },
                "required": ["id", "name"],
                "title": "Team",
                "type": "object",
            },
            "Tournament_zh4alg_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 32767,
                        "minimum": -32768,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 255, "title": "Name", "type": "string"},
                    "desc": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": None,
                        "nullable": True,
                        "title": "Desc",
                    },
                    "created": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Created",
                        "type": "string",
                    },
                },
                "required": ["id", "name", "created"],
                "title": "Tournament",
                "type": "object",
            },
        },
        "additionalProperties": False,
        "description": "Events on the calendar",
        "properties": {
            "event_id": {
                "maximum": 9223372036854775807,
                "minimum": -9223372036854775808,
                "title": "Event Id",
                "type": "integer",
            },
            "name": {"description": "The name", "title": "Name", "type": "string"},
            "tournament": {
                "$ref": "#/$defs/Tournament_zh4alg_leaf",
                "description": "What tournaments is a happenin'",
            },
            "reporter": {
                "anyOf": [
                    {"$ref": "#/$defs/Reporter_ifqfo2_leaf"},
                    {"type": "null"},
                ],
                "default": None,
                "nullable": True,
                "title": "Reporter",
            },
            "participants": {
                "items": {"$ref": "#/$defs/Team_fcszy2_leaf"},
                "title": "Participants",
                "type": "array",
            },
            "modified": {
                "format": "date-time",
                "readOnly": True,
                "title": "Modified",
                "type": "string",
            },
            "token": {"title": "Token", "type": "string"},
            "alias": {
                "anyOf": [
                    {"maximum": 2147483647, "minimum": -2147483648, "type": "integer"},
                    {"type": "null"},
                ],
                "default": None,
                "nullable": True,
                "title": "Alias",
            },
            "address": {
                "anyOf": [
                    {"$ref": "#/$defs/Address_zwygvk_leaf"},
                    {"type": "null"},
                ],
                "default": None,
                "nullable": True,
                "title": "Address",
            },
        },
        "required": [
            "event_id",
            "name",
            "tournament",
            "participants",
            "modified",
            "token",
        ],
        "title": "Event",
        "type": "object",
    }


@pytest.mark.asyncio
async def test_eventlist_schema(db, pydantic_setup):
    Event_Pydantic_List = pydantic_setup["Event_Pydantic_List"]
    assert Event_Pydantic_List.model_json_schema() == {
        "$defs": {
            "Event_rgfzbr": {
                "additionalProperties": False,
                "description": "Events on the calendar",
                "properties": {
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                    "name": {"description": "The name", "title": "Name", "type": "string"},
                    "tournament": {
                        "$ref": "#/$defs/Tournament_zh4alg_leaf",
                        "description": "What tournaments is a happenin'",
                    },
                    "reporter": {
                        "anyOf": [
                            {"$ref": "#/$defs/Reporter_ifqfo2_leaf"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Reporter",
                    },
                    "participants": {
                        "items": {"$ref": "#/$defs/Team_fcszy2_leaf"},
                        "title": "Participants",
                        "type": "array",
                    },
                    "modified": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Modified",
                        "type": "string",
                    },
                    "token": {"title": "Token", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                    "address": {
                        "anyOf": [
                            {"$ref": "#/$defs/Address_zwygvk_leaf"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Address",
                    },
                },
                "required": [
                    "event_id",
                    "name",
                    "tournament",
                    "participants",
                    "modified",
                    "token",
                ],
                "title": "Event",
                "type": "object",
            },
            "Address_zwygvk_leaf": {
                "additionalProperties": False,
                "properties": {
                    "city": {"maxLength": 64, "title": "City", "type": "string"},
                    "street": {"maxLength": 128, "title": "Street", "type": "string"},
                    "m2mwitho2opks": {
                        "items": {"$ref": "#/$defs/M2mWithO2oPk_zpacbp_leaf"},
                        "title": "M2Mwitho2Opks",
                        "type": "array",
                    },
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                },
                "required": ["city", "street", "event_id", "m2mwitho2opks"],
                "title": "Address",
                "type": "object",
            },
            "M2mWithO2oPk_zpacbp_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 64, "title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "M2mWithO2oPk",
                "type": "object",
            },
            "Reporter_ifqfo2_leaf": {
                "additionalProperties": False,
                "description": "Whom is assigned as the reporter",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "Reporter",
                "type": "object",
            },
            "Team_fcszy2_leaf": {
                "additionalProperties": False,
                "description": "Team that is a playing",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                },
                "required": ["id", "name"],
                "title": "Team",
                "type": "object",
            },
            "Tournament_zh4alg_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 32767,
                        "minimum": -32768,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 255, "title": "Name", "type": "string"},
                    "desc": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": None,
                        "nullable": True,
                        "title": "Desc",
                    },
                    "created": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Created",
                        "type": "string",
                    },
                },
                "required": ["id", "name", "created"],
                "title": "Tournament",
                "type": "object",
            },
        },
        "description": "Events on the calendar",
        "items": {"$ref": "#/$defs/Event_rgfzbr"},
        "title": "Event_list",
        "type": "array",
    }


@pytest.mark.asyncio
async def test_address_schema(db, pydantic_setup):
    Address_Pydantic = pydantic_setup["Address_Pydantic"]
    assert Address_Pydantic.model_json_schema() == {
        "$defs": {
            "Event_bhjepe_leaf": {
                "additionalProperties": False,
                "description": "Events on the calendar",
                "properties": {
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                    "name": {"description": "The name", "title": "Name", "type": "string"},
                    "tournament": {
                        "$ref": "#/$defs/Tournament_zh4alg_leaf",
                        "description": "What tournaments is a happenin'",
                    },
                    "reporter": {
                        "anyOf": [
                            {"$ref": "#/$defs/Reporter_ifqfo2_leaf"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Reporter",
                    },
                    "participants": {
                        "items": {"$ref": "#/$defs/Team_fcszy2_leaf"},
                        "title": "Participants",
                        "type": "array",
                    },
                    "modified": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Modified",
                        "type": "string",
                    },
                    "token": {"title": "Token", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                },
                "required": [
                    "event_id",
                    "name",
                    "tournament",
                    "participants",
                    "modified",
                    "token",
                ],
                "title": "Event",
                "type": "object",
            },
            "M2mWithO2oPk_zpacbp_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 64, "title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "M2mWithO2oPk",
                "type": "object",
            },
            "Reporter_ifqfo2_leaf": {
                "additionalProperties": False,
                "description": "Whom is assigned as the reporter",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "Reporter",
                "type": "object",
            },
            "Team_fcszy2_leaf": {
                "additionalProperties": False,
                "description": "Team that is a playing",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                },
                "required": ["id", "name"],
                "title": "Team",
                "type": "object",
            },
            "Tournament_zh4alg_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 32767,
                        "minimum": -32768,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 255, "title": "Name", "type": "string"},
                    "desc": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": None,
                        "nullable": True,
                        "title": "Desc",
                    },
                    "created": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Created",
                        "type": "string",
                    },
                },
                "required": ["id", "name", "created"],
                "title": "Tournament",
                "type": "object",
            },
        },
        "additionalProperties": False,
        "properties": {
            "city": {"maxLength": 64, "title": "City", "type": "string"},
            "street": {"maxLength": 128, "title": "Street", "type": "string"},
            "m2mwitho2opks": {
                "items": {"$ref": "#/$defs/M2mWithO2oPk_zpacbp_leaf"},
                "title": "M2Mwitho2Opks",
                "type": "array",
            },
            "event": {"$ref": "#/$defs/Event_bhjepe_leaf"},
            "event_id": {
                "maximum": 9223372036854775807,
                "minimum": -9223372036854775808,
                "title": "Event Id",
                "type": "integer",
            },
        },
        "required": ["city", "street", "event", "event_id", "m2mwitho2opks"],
        "title": "Address",
        "type": "object",
    }


@pytest.mark.asyncio
async def test_tournament_schema(db, pydantic_setup):
    Tournament_Pydantic = pydantic_setup["Tournament_Pydantic"]
    assert Tournament_Pydantic.model_json_schema() == {
        "$defs": {
            "Event_tymecz_leaf": {
                "additionalProperties": False,
                "description": "Events on the calendar",
                "properties": {
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                    "name": {"description": "The name", "title": "Name", "type": "string"},
                    "reporter": {
                        "anyOf": [
                            {"$ref": "#/$defs/Reporter_ifqfo2_leaf"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Reporter",
                    },
                    "participants": {
                        "items": {"$ref": "#/$defs/Team_fcszy2_leaf"},
                        "title": "Participants",
                        "type": "array",
                    },
                    "modified": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Modified",
                        "type": "string",
                    },
                    "token": {"title": "Token", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                    "address": {
                        "anyOf": [
                            {"$ref": "#/$defs/Address_zwygvk_leaf"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Address",
                    },
                },
                "required": [
                    "event_id",
                    "name",
                    "participants",
                    "modified",
                    "token",
                ],
                "title": "Event",
                "type": "object",
            },
            "Address_zwygvk_leaf": {
                "additionalProperties": False,
                "properties": {
                    "city": {"maxLength": 64, "title": "City", "type": "string"},
                    "street": {"maxLength": 128, "title": "Street", "type": "string"},
                    "m2mwitho2opks": {
                        "items": {"$ref": "#/$defs/M2mWithO2oPk_zpacbp_leaf"},
                        "title": "M2Mwitho2Opks",
                        "type": "array",
                    },
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                },
                "required": ["city", "street", "event_id", "m2mwitho2opks"],
                "title": "Address",
                "type": "object",
            },
            "M2mWithO2oPk_zpacbp_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 64, "title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "M2mWithO2oPk",
                "type": "object",
            },
            "Reporter_ifqfo2_leaf": {
                "additionalProperties": False,
                "description": "Whom is assigned as the reporter",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "Reporter",
                "type": "object",
            },
            "Team_fcszy2_leaf": {
                "additionalProperties": False,
                "description": "Team that is a playing",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                },
                "required": ["id", "name"],
                "title": "Team",
                "type": "object",
            },
        },
        "additionalProperties": False,
        "properties": {
            "id": {"maximum": 32767, "minimum": -32768, "title": "Id", "type": "integer"},
            "name": {"maxLength": 255, "title": "Name", "type": "string"},
            "desc": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
                "nullable": True,
                "title": "Desc",
            },
            "created": {
                "format": "date-time",
                "readOnly": True,
                "title": "Created",
                "type": "string",
            },
            "events": {
                "description": "What tournaments is a happenin'",
                "items": {"$ref": "#/$defs/Event_tymecz_leaf"},
                "title": "Events",
                "type": "array",
            },
        },
        "required": ["id", "name", "created", "events"],
        "title": "Tournament",
        "type": "object",
    }


@pytest.mark.asyncio
async def test_team_schema(db, pydantic_setup):
    Team_Pydantic = pydantic_setup["Team_Pydantic"]
    assert Team_Pydantic.model_json_schema() == {
        "$defs": {
            "Event_3zjun4_leaf": {
                "additionalProperties": False,
                "description": "Events on the calendar",
                "properties": {
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                    "name": {"description": "The name", "title": "Name", "type": "string"},
                    "tournament": {
                        "$ref": "#/$defs/Tournament_zh4alg_leaf",
                        "description": "What tournaments is a happenin'",
                    },
                    "reporter": {
                        "anyOf": [
                            {"$ref": "#/$defs/Reporter_ifqfo2_leaf"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Reporter",
                    },
                    "modified": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Modified",
                        "type": "string",
                    },
                    "token": {"title": "Token", "type": "string"},
                    "alias": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Alias",
                    },
                    "address": {
                        "anyOf": [
                            {"$ref": "#/$defs/Address_zwygvk_leaf"},
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Address",
                    },
                },
                "required": [
                    "event_id",
                    "name",
                    "tournament",
                    "modified",
                    "token",
                ],
                "title": "Event",
                "type": "object",
            },
            "Address_zwygvk_leaf": {
                "additionalProperties": False,
                "properties": {
                    "city": {"maxLength": 64, "title": "City", "type": "string"},
                    "street": {"maxLength": 128, "title": "Street", "type": "string"},
                    "m2mwitho2opks": {
                        "items": {"$ref": "#/$defs/M2mWithO2oPk_zpacbp_leaf"},
                        "title": "M2Mwitho2Opks",
                        "type": "array",
                    },
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                },
                "required": ["city", "street", "event_id", "m2mwitho2opks"],
                "title": "Address",
                "type": "object",
            },
            "M2mWithO2oPk_zpacbp_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 64, "title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "M2mWithO2oPk",
                "type": "object",
            },
            "Reporter_ifqfo2_leaf": {
                "additionalProperties": False,
                "description": "Whom is assigned as the reporter",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"title": "Name", "type": "string"},
                },
                "required": ["id", "name"],
                "title": "Reporter",
                "type": "object",
            },
            "Tournament_zh4alg_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 32767,
                        "minimum": -32768,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 255, "title": "Name", "type": "string"},
                    "desc": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": None,
                        "nullable": True,
                        "title": "Desc",
                    },
                    "created": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Created",
                        "type": "string",
                    },
                },
                "required": ["id", "name", "created"],
                "title": "Tournament",
                "type": "object",
            },
        },
        "additionalProperties": False,
        "description": "Team that is a playing",
        "properties": {
            "id": {
                "maximum": 2147483647,
                "minimum": -2147483648,
                "title": "Id",
                "type": "integer",
            },
            "name": {"title": "Name", "type": "string"},
            "alias": {
                "anyOf": [
                    {"maximum": 2147483647, "minimum": -2147483648, "type": "integer"},
                    {"type": "null"},
                ],
                "default": None,
                "nullable": True,
                "title": "Alias",
            },
            "events": {
                "items": {"$ref": "#/$defs/Event_3zjun4_leaf"},
                "title": "Events",
                "type": "array",
            },
        },
        "required": ["id", "name", "events"],
        "title": "Team",
        "type": "object",
    }


@pytest.mark.asyncio
async def test_eventlist(db, pydantic_setup):
    Event_Pydantic_List = pydantic_setup["Event_Pydantic_List"]
    event = pydantic_setup["event"]
    event2 = pydantic_setup["event2"]
    tournament = pydantic_setup["tournament"]
    reporter = pydantic_setup["reporter"]
    team1 = pydantic_setup["team1"]
    team2 = pydantic_setup["team2"]
    address = pydantic_setup["address"]

    eventlp = await Event_Pydantic_List.from_queryset(Event.all())
    eventldict = eventlp.model_dump()

    # Remove timestamps
    del eventldict[0]["modified"]
    del eventldict[0]["tournament"]["created"]
    del eventldict[1]["modified"]
    del eventldict[1]["tournament"]["created"]

    assert eventldict == [
        {
            "event_id": event.event_id,
            "name": "Test",
            # "modified": "2020-01-28T10:43:50.901562",
            "token": event.token,
            "alias": None,
            "tournament": {
                "id": tournament.id,
                "name": "New Tournament",
                "desc": None,
                # "created": "2020-01-28T10:43:50.900664"
            },
            "reporter": {"id": reporter.id, "name": "The Reporter"},
            "participants": [
                {"id": team1.id, "name": "Onesies", "alias": None},
                {"id": team2.id, "name": "T-Shirts", "alias": None},
            ],
            "address": {
                "event_id": address.pk,
                "city": "Santa Monica",
                "m2mwitho2opks": [],
                "street": "Ocean",
            },
        },
        {
            "event_id": event2.event_id,
            "name": "Test2",
            # "modified": "2020-01-28T10:43:50.901562",
            "token": event2.token,
            "alias": None,
            "tournament": {
                "id": tournament.id,
                "name": "New Tournament",
                "desc": None,
                # "created": "2020-01-28T10:43:50.900664"
            },
            "reporter": None,
            "participants": [
                {"id": team1.id, "name": "Onesies", "alias": None},
                {"id": team2.id, "name": "T-Shirts", "alias": None},
            ],
            "address": None,
        },
    ]


@pytest.mark.asyncio
async def test_event(db, pydantic_setup):
    Event_Pydantic = pydantic_setup["Event_Pydantic"]
    event = pydantic_setup["event"]
    tournament = pydantic_setup["tournament"]
    reporter = pydantic_setup["reporter"]
    team1 = pydantic_setup["team1"]
    team2 = pydantic_setup["team2"]
    address = pydantic_setup["address"]

    eventp = await Event_Pydantic.from_tortoise_orm(await Event.get(name="Test"))
    eventdict = eventp.model_dump()

    # Remove timestamps
    del eventdict["modified"]
    del eventdict["tournament"]["created"]

    assert eventdict == {
        "event_id": event.event_id,
        "name": "Test",
        # "modified": "2020-01-28T10:43:50.901562",
        "token": event.token,
        "alias": None,
        "tournament": {
            "id": tournament.id,
            "name": "New Tournament",
            "desc": None,
            # "created": "2020-01-28T10:43:50.900664"
        },
        "reporter": {"id": reporter.id, "name": "The Reporter"},
        "participants": [
            {"id": team1.id, "name": "Onesies", "alias": None},
            {"id": team2.id, "name": "T-Shirts", "alias": None},
        ],
        "address": {
            "event_id": address.pk,
            "city": "Santa Monica",
            "m2mwitho2opks": [],
            "street": "Ocean",
        },
    }


@pytest.mark.asyncio
async def test_address(db, pydantic_setup):
    Address_Pydantic = pydantic_setup["Address_Pydantic"]
    event = pydantic_setup["event"]
    tournament = pydantic_setup["tournament"]
    reporter = pydantic_setup["reporter"]
    team1 = pydantic_setup["team1"]
    team2 = pydantic_setup["team2"]
    address = pydantic_setup["address"]

    addressp = await Address_Pydantic.from_tortoise_orm(await Address.get(street="Ocean"))
    addressdict = addressp.model_dump()

    # Remove timestamps
    del addressdict["event"]["tournament"]["created"]
    del addressdict["event"]["modified"]

    assert addressdict == {
        "city": "Santa Monica",
        "street": "Ocean",
        "event": {
            "event_id": event.event_id,
            "name": "Test",
            "tournament": {
                "id": tournament.id,
                "name": "New Tournament",
                "desc": None,
            },
            "reporter": {"id": reporter.id, "name": "The Reporter"},
            "participants": [
                {"id": team1.id, "name": "Onesies", "alias": None},
                {"id": team2.id, "name": "T-Shirts", "alias": None},
            ],
            "token": event.token,
            "alias": None,
        },
        "event_id": address.event_id,
        "m2mwitho2opks": [],
    }


@pytest.mark.asyncio
async def test_tournament(db, pydantic_setup):
    Tournament_Pydantic = pydantic_setup["Tournament_Pydantic"]
    event = pydantic_setup["event"]
    event2 = pydantic_setup["event2"]
    tournament = pydantic_setup["tournament"]
    reporter = pydantic_setup["reporter"]
    team1 = pydantic_setup["team1"]
    team2 = pydantic_setup["team2"]
    address = pydantic_setup["address"]

    tournamentp = await Tournament_Pydantic.from_tortoise_orm(await Tournament.all().first())
    tournamentdict = tournamentp.model_dump()

    # Remove timestamps
    del tournamentdict["events"][0]["modified"]
    del tournamentdict["events"][1]["modified"]
    del tournamentdict["created"]

    assert tournamentdict == {
        "id": tournament.id,
        "name": "New Tournament",
        "desc": None,
        # "created": "2020-01-28T19:41:38.059617",
        "events": [
            {
                "event_id": event.event_id,
                "name": "Test",
                # "modified": "2020-01-28T19:41:38.060070",
                "token": event.token,
                "alias": None,
                "reporter": {"id": reporter.id, "name": "The Reporter"},
                "participants": [
                    {"id": team1.id, "name": "Onesies", "alias": None},
                    {"id": team2.id, "name": "T-Shirts", "alias": None},
                ],
                "address": {
                    "event_id": address.pk,
                    "city": "Santa Monica",
                    "m2mwitho2opks": [],
                    "street": "Ocean",
                },
            },
            {
                "event_id": event2.event_id,
                "name": "Test2",
                # "modified": "2020-01-28T19:41:38.060070",
                "token": event2.token,
                "alias": None,
                "reporter": None,
                "participants": [
                    {"id": team1.id, "name": "Onesies", "alias": None},
                    {"id": team2.id, "name": "T-Shirts", "alias": None},
                ],
                "address": None,
            },
        ],
    }


@pytest.mark.asyncio
async def test_team(db, pydantic_setup):
    Team_Pydantic = pydantic_setup["Team_Pydantic"]
    event = pydantic_setup["event"]
    event2 = pydantic_setup["event2"]
    tournament = pydantic_setup["tournament"]
    reporter = pydantic_setup["reporter"]
    team1 = pydantic_setup["team1"]
    address = pydantic_setup["address"]

    teamp = await Team_Pydantic.from_tortoise_orm(await Team.get(id=team1.id))
    teamdict = teamp.model_dump()

    # Remove timestamps
    del teamdict["events"][0]["modified"]
    del teamdict["events"][0]["tournament"]["created"]
    del teamdict["events"][1]["modified"]
    del teamdict["events"][1]["tournament"]["created"]

    assert teamdict == {
        "id": team1.id,
        "name": "Onesies",
        "alias": None,
        "events": [
            {
                "event_id": event.event_id,
                "name": "Test",
                # "modified": "2020-01-28T19:47:03.334077",
                "token": event.token,
                "alias": None,
                "tournament": {
                    "id": tournament.id,
                    "name": "New Tournament",
                    "desc": None,
                    # "created": "2020-01-28T19:41:38.059617",
                },
                "reporter": {"id": reporter.id, "name": "The Reporter"},
                "address": {
                    "event_id": address.pk,
                    "city": "Santa Monica",
                    "m2mwitho2opks": [],
                    "street": "Ocean",
                },
            },
            {
                "event_id": event2.event_id,
                "name": "Test2",
                # "modified": "2020-01-28T19:47:03.334077",
                "token": event2.token,
                "alias": None,
                "tournament": {
                    "id": tournament.id,
                    "name": "New Tournament",
                    "desc": None,
                    # "created": "2020-01-28T19:41:38.059617",
                },
                "reporter": None,
                "address": None,
            },
        ],
    }


@pytest.mark.asyncio
async def test_event_named(db, pydantic_setup):
    Event_Named = pydantic_model_creator(Event, name="Foo")
    schema = Event_Named.model_json_schema()
    assert schema["title"] == "Foo"
    assert set(schema["properties"].keys()) == {
        "address",
        "alias",
        "event_id",
        "modified",
        "name",
        "participants",
        "reporter",
        "token",
        "tournament",
    }


@pytest.mark.asyncio
async def test_event_sorted(db, pydantic_setup):
    Event_Named = pydantic_model_creator(Event, sort_alphabetically=True)
    schema = Event_Named.model_json_schema()
    assert list(schema["properties"].keys()) == [
        "address",
        "alias",
        "event_id",
        "modified",
        "name",
        "participants",
        "reporter",
        "token",
        "tournament",
    ]


@pytest.mark.asyncio
async def test_event_unsorted(db, pydantic_setup):
    Event_Named = pydantic_model_creator(Event, sort_alphabetically=False)
    schema = Event_Named.model_json_schema()
    assert list(schema["properties"].keys()) == [
        "event_id",
        "name",
        "tournament",
        "reporter",
        "participants",
        "modified",
        "token",
        "alias",
        "address",
    ]


@pytest.mark.asyncio
async def test_json_field(db):
    json_field_0 = await JSONFields.create(data={"a": 1})
    json_field_1 = await JSONFields.create(data=[{"a": 1, "b": 2}])
    json_field_0_get = await JSONFields.get(pk=json_field_0.pk)
    json_field_1_get = await JSONFields.get(pk=json_field_1.pk)

    creator = pydantic_model_creator(JSONFields)
    ret0 = creator.model_validate(json_field_0_get).model_dump()
    assert ret0 == {
        "id": json_field_0.pk,
        "data": {"a": 1},
        "data_null": None,
        "data_default": {"a": 1},
        "data_validate": None,
        "data_pydantic": json_pydantic_default.model_dump(),
    }
    ret1 = creator.model_validate(json_field_1_get).model_dump()
    assert ret1 == {
        "id": json_field_1.pk,
        "data": [{"a": 1, "b": 2}],
        "data_null": None,
        "data_default": {"a": 1},
        "data_validate": None,
        "data_pydantic": json_pydantic_default.model_dump(),
    }


def test_override_default_model_config_by_config_class(db):
    """Pydantic meta's config_class should be able to override default config."""
    # Save original value to restore after test
    original_value = CamelCaseAliasPerson.PydanticMeta.model_config.get("from_attributes")
    try:
        # Set class pydantic config's from_attributes to False
        CamelCaseAliasPerson.PydanticMeta.model_config["from_attributes"] = False

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson, name="AutoAliasPersonOverriddenORMMode"
        )

        assert ModelPydantic.model_config["from_attributes"] is False
    finally:
        # Restore original value to avoid polluting other tests
        if original_value is None:
            CamelCaseAliasPerson.PydanticMeta.model_config.pop("from_attributes", None)
        else:
            CamelCaseAliasPerson.PydanticMeta.model_config["from_attributes"] = original_value


def test_override_meta_pydantic_config_by_model_creator(db):
    model_config = ConfigDict(title="Another title!")

    ModelPydantic = pydantic_model_creator(
        CamelCaseAliasPerson,
        model_config=model_config,
        name="AutoAliasPersonModelCreatorConfig",
    )

    assert model_config["title"] == ModelPydantic.model_config["title"]


def test_config_classes_merge_all_configs(db):
    """Model creator should merge all 3 configs.

    - It merges (Default, Meta's config_class and creator's config_class) together.
    """
    model_config = ConfigDict(str_min_length=3)

    ModelPydantic = pydantic_model_creator(
        CamelCaseAliasPerson, name="AutoAliasPersonMinLength", model_config=model_config
    )

    # Should set min_anystr_length from pydantic_model_creator's config
    assert ModelPydantic.model_config["str_min_length"] == model_config["str_min_length"]
    # Should set title from model PydanticMeta's config
    assert (
        ModelPydantic.model_config["title"]
        == CamelCaseAliasPerson.PydanticMeta.model_config["title"]
    )
    # Should set orm_mode from base pydantic model configuration
    assert (
        ModelPydantic.model_config["from_attributes"]
        == PydanticModel.model_config["from_attributes"]
    )


def test_exclude_readonly(db):
    ModelPydantic = pydantic_model_creator(Event, exclude_readonly=True)

    assert "modified" not in ModelPydantic.model_json_schema()["properties"]


# Fixtures for TestPydanticCycle
@pytest_asyncio.fixture
async def pydantic_cycle_setup(db):
    """Setup for pydantic cycle tests with employee hierarchy."""
    Employee_Pydantic = pydantic_model_creator(Employee)

    root = await Employee.create(name="Root")
    loose = await Employee.create(name="Loose")
    _1 = await Employee.create(name="1. First H1", manager=root)
    _2 = await Employee.create(name="2. Second H1", manager=root)
    _1_1 = await Employee.create(name="1.1. First H2", manager=_1)
    _1_1_1 = await Employee.create(name="1.1.1. First H3", manager=_1_1)
    _2_1 = await Employee.create(name="2.1. Second H2", manager=_2)
    _2_2 = await Employee.create(name="2.2. Third H2", manager=_2)

    await _1.talks_to.add(_2, _1_1_1, loose)
    await _2_1.gets_talked_to.add(_2_2, _1_1, loose)

    return {
        "Employee_Pydantic": Employee_Pydantic,
        "root": root,
        "loose": loose,
        "_1": _1,
        "_2": _2,
        "_1_1": _1_1,
        "_1_1_1": _1_1_1,
        "_2_1": _2_1,
        "_2_2": _2_2,
    }


@pytest.mark.asyncio
async def test_cycle_schema(db, pydantic_cycle_setup):
    Employee_Pydantic = pydantic_cycle_setup["Employee_Pydantic"]
    assert Employee_Pydantic.model_json_schema() == {
        "$defs": {
            "Employee_eywjnx_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 50, "title": "Name", "type": "string"},
                    "talks_to": {
                        "items": {"$ref": "#/$defs/Employee_ic5xpw_leaf"},
                        "title": "Talks To",
                        "type": "array",
                    },
                    "manager_id": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Manager Id",
                    },
                    "team_members": {
                        "items": {"$ref": "#/$defs/Employee_ic5xpw_leaf"},
                        "title": "Team Members",
                        "type": "array",
                    },
                },
                "required": ["id", "name", "talks_to", "team_members"],
                "title": "Employee",
                "type": "object",
            },
            "Employee_ic5xpw_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 50, "title": "Name", "type": "string"},
                    "manager_id": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Manager Id",
                    },
                },
                "required": ["id", "name"],
                "title": "Employee",
                "type": "object",
            },
        },
        "additionalProperties": False,
        "properties": {
            "id": {
                "maximum": 2147483647,
                "minimum": -2147483648,
                "title": "Id",
                "type": "integer",
            },
            "name": {"maxLength": 50, "title": "Name", "type": "string"},
            "talks_to": {
                "items": {"$ref": "#/$defs/Employee_eywjnx_leaf"},
                "title": "Talks To",
                "type": "array",
            },
            "manager_id": {
                "anyOf": [
                    {"maximum": 2147483647, "minimum": -2147483648, "type": "integer"},
                    {"type": "null"},
                ],
                "default": None,
                "nullable": True,
                "title": "Manager Id",
            },
            "team_members": {
                "items": {"$ref": "#/$defs/Employee_eywjnx_leaf"},
                "title": "Team Members",
                "type": "array",
            },
        },
        "required": ["id", "name", "talks_to", "team_members"],
        "title": "Employee",
        "type": "object",
    }


@pytest.mark.asyncio
async def test_cycle_serialisation(db, pydantic_cycle_setup):
    Employee_Pydantic = pydantic_cycle_setup["Employee_Pydantic"]
    root = pydantic_cycle_setup["root"]
    loose = pydantic_cycle_setup["loose"]
    _1 = pydantic_cycle_setup["_1"]
    _2 = pydantic_cycle_setup["_2"]
    _1_1 = pydantic_cycle_setup["_1_1"]
    _1_1_1 = pydantic_cycle_setup["_1_1_1"]
    _2_1 = pydantic_cycle_setup["_2_1"]
    _2_2 = pydantic_cycle_setup["_2_2"]

    empp = await Employee_Pydantic.from_tortoise_orm(await Employee.get(name="Root"))
    empdict = empp.model_dump()

    assert empdict == {
        "id": root.id,
        "manager_id": None,
        "name": "Root",
        "talks_to": [],
        "team_members": [
            {
                "id": _1.id,
                "manager_id": root.id,
                "name": "1. First H1",
                "talks_to": [
                    {
                        "id": loose.id,
                        "manager_id": None,
                        "name": "Loose",
                        "name_length": 5,
                        "team_size": 0,
                    },
                    {
                        "id": _2.id,
                        "manager_id": root.id,
                        "name": "2. Second H1",
                        "name_length": 12,
                        "team_size": 0,
                    },
                    {
                        "id": _1_1_1.id,
                        "manager_id": _1_1.id,
                        "name": "1.1.1. First H3",
                        "name_length": 15,
                        "team_size": 0,
                    },
                ],
                "team_members": [
                    {
                        "id": _1_1.id,
                        "manager_id": _1.id,
                        "name": "1.1. First H2",
                        "name_length": 13,
                        "team_size": 0,
                    }
                ],
                "name_length": 11,
                "team_size": 1,
            },
            {
                "id": _2.id,
                "manager_id": root.id,
                "name": "2. Second H1",
                "talks_to": [],
                "team_members": [
                    {
                        "id": _2_1.id,
                        "manager_id": _2.id,
                        "name": "2.1. Second H2",
                        "name_length": 14,
                        "team_size": 0,
                    },
                    {
                        "id": _2_2.id,
                        "manager_id": _2.id,
                        "name": "2.2. Third H2",
                        "name_length": 13,
                        "team_size": 0,
                    },
                ],
                "name_length": 12,
                "team_size": 2,
            },
        ],
        "name_length": 4,
        "team_size": 2,
    }


# Fixtures for TestPydanticComputed
@pytest_asyncio.fixture
async def pydantic_computed_setup(db):
    """Setup for pydantic computed field tests."""
    Employee_Pydantic = pydantic_model_creator(Employee)
    employee = await Employee.create(name="Some Employee")

    return {
        "Employee_Pydantic": Employee_Pydantic,
        "employee": employee,
    }


@pytest.mark.asyncio
async def test_computed_field(db, pydantic_computed_setup):
    Employee_Pydantic = pydantic_computed_setup["Employee_Pydantic"]
    employee = pydantic_computed_setup["employee"]

    employee_pyd = await Employee_Pydantic.from_tortoise_orm(
        await Employee.get(name="Some Employee")
    )
    employee_serialised = employee_pyd.model_dump()
    assert employee_serialised.get("name_length") == employee.name_length()


@pytest.mark.asyncio
async def test_computed_field_schema(db, pydantic_computed_setup):
    Employee_Pydantic = pydantic_computed_setup["Employee_Pydantic"]
    assert Employee_Pydantic.model_json_schema(mode="serialization") == {
        "$defs": {
            "Employee_ic5xpw_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 50, "title": "Name", "type": "string"},
                    "manager_id": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Manager Id",
                    },
                    "name_length": {
                        "description": "",
                        "readOnly": True,
                        "title": "Name Length",
                        "type": "integer",
                    },
                    "team_size": {
                        "description": "Computes team size.<br/><br/>Note that this function needs to be annotated with a return type so that pydantic can<br/> generate a valid schema.<br/><br/>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br/> pre-fetch relational data, so that it is available before serialization. So we don't<br/> need to await the relation. We do however have to protect against the case where no<br/> prefetching was done, hence catching and handling the<br/> ``tortoise.exceptions.NoValuesFetched`` exception.",
                        "readOnly": True,
                        "title": "Team Size",
                        "type": "integer",
                    },
                },
                "required": ["id", "name", "name_length", "team_size"],
                "title": "Employee",
                "type": "object",
            },
            "Employee_eywjnx_leaf": {
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {"maxLength": 50, "title": "Name", "type": "string"},
                    "talks_to": {
                        "items": {"$ref": "#/$defs/Employee_ic5xpw_leaf"},
                        "title": "Talks To",
                        "type": "array",
                    },
                    "manager_id": {
                        "anyOf": [
                            {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "type": "integer",
                            },
                            {"type": "null"},
                        ],
                        "default": None,
                        "nullable": True,
                        "title": "Manager Id",
                    },
                    "team_members": {
                        "items": {"$ref": "#/$defs/Employee_ic5xpw_leaf"},
                        "title": "Team Members",
                        "type": "array",
                    },
                    "name_length": {
                        "description": "",
                        "readOnly": True,
                        "title": "Name Length",
                        "type": "integer",
                    },
                    "team_size": {
                        "description": "Computes team size.<br/><br/>Note that this function needs to be annotated with a return type so that pydantic can<br/> generate a valid schema.<br/><br/>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br/> pre-fetch relational data, so that it is available before serialization. So we don't<br/> need to await the relation. We do however have to protect against the case where no<br/> prefetching was done, hence catching and handling the<br/> ``tortoise.exceptions.NoValuesFetched`` exception.",
                        "readOnly": True,
                        "title": "Team Size",
                        "type": "integer",
                    },
                },
                "required": [
                    "id",
                    "name",
                    "talks_to",
                    "team_members",
                    "name_length",
                    "team_size",
                ],
                "title": "Employee",
                "type": "object",
            },
        },
        "additionalProperties": False,
        "properties": {
            "id": {
                "maximum": 2147483647,
                "minimum": -2147483648,
                "title": "Id",
                "type": "integer",
            },
            "name": {"maxLength": 50, "title": "Name", "type": "string"},
            "talks_to": {
                "items": {"$ref": "#/$defs/Employee_eywjnx_leaf"},
                "title": "Talks To",
                "type": "array",
            },
            "manager_id": {
                "anyOf": [
                    {"maximum": 2147483647, "minimum": -2147483648, "type": "integer"},
                    {"type": "null"},
                ],
                "default": None,
                "nullable": True,
                "title": "Manager Id",
            },
            "team_members": {
                "items": {"$ref": "#/$defs/Employee_eywjnx_leaf"},
                "title": "Team Members",
                "type": "array",
            },
            "name_length": {
                "description": "",
                "readOnly": True,
                "title": "Name Length",
                "type": "integer",
            },
            "team_size": {
                "description": "Computes team size.<br/><br/>Note that this function needs to be annotated with a return type so that pydantic can<br/> generate a valid schema.<br/><br/>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br/> pre-fetch relational data, so that it is available before serialization. So we don't<br/> need to await the relation. We do however have to protect against the case where no<br/> prefetching was done, hence catching and handling the<br/> ``tortoise.exceptions.NoValuesFetched`` exception.",
                "readOnly": True,
                "title": "Team Size",
                "type": "integer",
            },
        },
        "required": ["id", "name", "talks_to", "team_members", "name_length", "team_size"],
        "title": "Employee",
        "type": "object",
    }


# Tests for TestPydanticUpdate
def test_create_schema(db):
    UserCreate_Pydantic = pydantic_model_creator(
        User,
        name="UserCreate",
        exclude_readonly=True,
    )
    assert UserCreate_Pydantic.model_json_schema() == {
        "title": "UserCreate",
        "type": "object",
        "properties": {
            "username": {
                "title": "Username",
                "maxLength": 32,
                "type": "string",
            },
            "mail": {
                "title": "Mail",
                "maxLength": 64,
                "type": "string",
            },
            "bio": {
                "title": "Bio",
                "type": "string",
            },
        },
        "required": [
            "username",
            "mail",
            "bio",
        ],
        "additionalProperties": False,
    }


def test_update_schema(db):
    """All fields of this schema should be optional.
    This demonstrates an example PATCH endpoint in an API, where a client may want
    to update a single field of a model without modifying the rest.
    """
    UserUpdate_Pydantic = pydantic_model_creator(
        User,
        name="UserUpdate",
        exclude_readonly=True,
        optional=("username", "mail", "bio"),
    )
    assert UserUpdate_Pydantic.model_json_schema() == {
        "additionalProperties": False,
        "properties": {
            "bio": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Bio",
            },
            "mail": {
                "anyOf": [{"maxLength": 64, "type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Mail",
            },
            "username": {
                "anyOf": [{"maxLength": 32, "type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Username",
            },
        },
        "title": "UserUpdate",
        "type": "object",
    }


# Tests for TestPydanticOptionalUpdate
def test_optional_update(db):
    UserUpdateAllOptional_Pydantic = pydantic_model_creator(
        User,
        name="UserUpdateAllOptional",
        exclude_readonly=True,
        optional=("username", "mail", "bio"),
    )
    UserUpdatePartialOptional_Pydantic = pydantic_model_creator(
        User,
        name="UserUpdatePartialOptional",
        exclude_readonly=True,
        optional=("username", "mail"),
    )
    UserUpdateWithoutOptional_Pydantic = pydantic_model_creator(
        User,
        name="UserUpdateWithoutOptional",
        exclude_readonly=True,
    )

    # All fields are optional
    assert UserUpdateAllOptional_Pydantic().model_dump(exclude_unset=True) == {}
    assert UserUpdateAllOptional_Pydantic(bio="foo").model_dump(exclude_unset=True) == {
        "bio": "foo"
    }
    assert UserUpdateAllOptional_Pydantic(username="name", mail="a@example.com").model_dump(
        exclude_unset=True
    ) == {"username": "name", "mail": "a@example.com"}
    assert UserUpdateAllOptional_Pydantic(username="name", mail="a@example.com").model_dump() == {
        "username": "name",
        "mail": "a@example.com",
        "bio": None,
    }
    # Some fields are optional
    with pytest.raises(ValidationError):
        UserUpdatePartialOptional_Pydantic()
    with pytest.raises(ValidationError):
        UserUpdatePartialOptional_Pydantic(username="name")
    assert UserUpdatePartialOptional_Pydantic(bio="foo").model_dump(exclude_unset=True) == {
        "bio": "foo"
    }
    assert UserUpdatePartialOptional_Pydantic(
        username="name", mail="a@example.com", bio=""
    ).model_dump(exclude_unset=True) == {"username": "name", "mail": "a@example.com", "bio": ""}
    assert UserUpdatePartialOptional_Pydantic(mail="a@example.com", bio="").model_dump() == {
        "username": None,
        "mail": "a@example.com",
        "bio": "",
    }
    # None of the fields is optional
    with pytest.raises(ValidationError):
        UserUpdateWithoutOptional_Pydantic()
    with pytest.raises(ValidationError):
        UserUpdateWithoutOptional_Pydantic(username="name")
    with pytest.raises(ValidationError):
        UserUpdateWithoutOptional_Pydantic(username="name", email="")
    assert UserUpdateWithoutOptional_Pydantic(
        username="name", mail="a@example.com", bio=""
    ).model_dump() == {"username": "name", "mail": "a@example.com", "bio": ""}


# Tests for TestPydanticMutlipleModelUses
def test_no_relations_model_reused(db):
    NoRelationsModel = IntFields
    Pydantic1 = pydantic_model_creator(NoRelationsModel)
    Pydantic2 = pydantic_model_creator(NoRelationsModel)

    assert Pydantic1 is Pydantic2


def test_no_relations_model_one_exclude(db):
    NoRelationsModel = IntFields
    Pydantic1 = pydantic_model_creator(NoRelationsModel)
    Pydantic2 = pydantic_model_creator(NoRelationsModel, exclude=("id",))

    assert Pydantic1 is not Pydantic2
    assert "id" in Pydantic1.model_json_schema()["required"]
    assert "id" not in Pydantic2.model_json_schema()["required"]


def test_no_relations_model_both_exclude(db):
    NoRelationsModel = IntFields
    Pydantic1 = pydantic_model_creator(NoRelationsModel, exclude=("id",))
    Pydantic2 = pydantic_model_creator(NoRelationsModel, exclude=("id",))

    assert Pydantic1 is Pydantic2
    assert "id" not in Pydantic1.model_json_schema()["required"]
    assert "id" not in Pydantic2.model_json_schema()["required"]


def test_no_relations_model_exclude_diff(db):
    NoRelationsModel = IntFields
    Pydantic1 = pydantic_model_creator(NoRelationsModel, exclude=("id",))
    Pydantic2 = pydantic_model_creator(NoRelationsModel, exclude=("name",))

    assert Pydantic1 is not Pydantic2


def test_no_relations_model_exclude_readonly(db):
    NoRelationsModel = IntFields
    Pydantic1 = pydantic_model_creator(NoRelationsModel)
    Pydantic2 = pydantic_model_creator(NoRelationsModel, exclude_readonly=True)

    assert Pydantic1 is not Pydantic2
    assert "id" in Pydantic1.model_json_schema()["properties"]
    assert "id" not in Pydantic2.model_json_schema()["properties"]


def test_model_with_relations_reused(db):
    ModelWithRelations = Event
    Pydantic1 = pydantic_model_creator(ModelWithRelations)
    Pydantic2 = pydantic_model_creator(ModelWithRelations)

    assert Pydantic1 is Pydantic2


def test_model_with_relations_exclude(db):
    ModelWithRelations = Event
    Pydantic1 = pydantic_model_creator(ModelWithRelations)
    Pydantic2 = pydantic_model_creator(ModelWithRelations, exclude=("event_id",))

    assert Pydantic1 is not Pydantic2
    assert "event_id" in Pydantic1.model_json_schema()["properties"]
    assert "event_id" not in Pydantic2.model_json_schema()["properties"]


def test_model_with_relations_exclude_readonly(db):
    ModelWithRelations = Event
    Pydantic1 = pydantic_model_creator(ModelWithRelations)
    Pydantic2 = pydantic_model_creator(ModelWithRelations, exclude_readonly=True)

    assert Pydantic1 is not Pydantic2
    assert "event_id" in Pydantic1.model_json_schema()["properties"]
    assert "event_id" not in Pydantic2.model_json_schema()["properties"]


def test_named_no_relations_model(db):
    NoRelationsModel = IntFields
    Pydantic1 = pydantic_model_creator(NoRelationsModel, name="Foo")
    Pydantic2 = pydantic_model_creator(NoRelationsModel, name="Foo")

    assert Pydantic1 is Pydantic2


def test_named_model_with_relations(db):
    ModelWithRelations = Event
    Pydantic1 = pydantic_model_creator(ModelWithRelations, name="Foo")
    Pydantic2 = pydantic_model_creator(ModelWithRelations, name="Foo")

    assert Pydantic1 is Pydantic2


# Tests for TestPydanticEnum
def test_int_enum(db):
    EnumFields_Pydantic = pydantic_model_creator(EnumFields)
    with pytest.raises(ValidationError) as exc_info:
        EnumFields_Pydantic.model_validate({"id": 1, "service": 4, "currency": "HUF"})
    assert [
        {
            "type": "enum",
            "loc": ("service",),
            "msg": "Input should be 1, 2 or 3",
            "input": 4,
            "ctx": {"expected": "1, 2 or 3"},
        }
    ] == exc_info.value.errors(include_url=False)
    with pytest.raises(ValidationError) as exc_info:
        EnumFields_Pydantic.model_validate(
            {"id": 1, "service": "a string, not int", "currency": "HUF"}
        )
    assert [
        {
            "type": "enum",
            "loc": ("service",),
            "msg": "Input should be 1, 2 or 3",
            "input": "a string, not int",
            "ctx": {"expected": "1, 2 or 3"},
        }
    ] == exc_info.value.errors(include_url=False)


def test_str_enum(db):
    EnumFields_Pydantic = pydantic_model_creator(EnumFields)
    with pytest.raises(ValidationError) as exc_info:
        EnumFields_Pydantic.model_validate({"id": 1, "service": 3, "currency": "GoofyGooberDollar"})
    assert [
        {
            "type": "enum",
            "loc": ("currency",),
            "msg": "Input should be 'HUF', 'EUR' or 'USD'",
            "input": "GoofyGooberDollar",
            "ctx": {"expected": "'HUF', 'EUR' or 'USD'"},
        }
    ] == exc_info.value.errors(include_url=False)
    with pytest.raises(ValidationError) as exc_info:
        EnumFields_Pydantic.model_validate({"id": 1, "service": 3, "currency": 1})
    assert [
        {
            "type": "enum",
            "loc": ("currency",),
            "msg": "Input should be 'HUF', 'EUR' or 'USD'",
            "input": 1,
            "ctx": {"expected": "'HUF', 'EUR' or 'USD'"},
        }
    ] == exc_info.value.errors(include_url=False)


def test_enum(db):
    EnumFields_Pydantic = pydantic_model_creator(EnumFields)
    with pytest.raises(ValidationError) as exc_info:
        EnumFields_Pydantic.model_validate({"id": 1, "service": 4, "currency": 1})
    assert [
        {
            "type": "enum",
            "loc": ("service",),
            "msg": "Input should be 1, 2 or 3",
            "input": 4,
            "ctx": {"expected": "1, 2 or 3"},
        },
        {
            "type": "enum",
            "loc": ("currency",),
            "msg": "Input should be 'HUF', 'EUR' or 'USD'",
            "input": 1,
            "ctx": {"expected": "'HUF', 'EUR' or 'USD'"},
        },
    ] == exc_info.value.errors(include_url=False)

    # should simply not raise any error:
    EnumFields_Pydantic.model_validate({"id": 1, "service": 3, "currency": "HUF"})
    assert {
        "$defs": {
            "Currency": {
                "enum": ["HUF", "EUR", "USD"],
                "title": "Currency",
                "type": "string",
            },
            "Service": {"enum": [1, 2, 3], "title": "Service", "type": "integer"},
        },
        "additionalProperties": False,
        "properties": {
            "id": {
                "maximum": 2147483647,
                "minimum": -2147483648,
                "title": "Id",
                "type": "integer",
            },
            "service": {
                "$ref": "#/$defs/Service",
                "description": "python_programming: 1<br/>database_design: 2<br/>system_administration: 3",
                "ge": -32768,
                "le": 32767,
            },
            "currency": {
                "$ref": "#/$defs/Currency",
                "default": "HUF",
                "description": "HUF: HUF<br/>EUR: EUR<br/>USD: USD",
                "maxLength": 3,
            },
        },
        "required": ["id", "service"],
        "title": "EnumFields",
        "type": "object",
    } == EnumFields_Pydantic.model_json_schema()


def test_nullable_fk_not_required(db):
    """Nullable FK/O2O relation fields should be optional (default=None) in the schema,
    not marked as required. This is the fix for issue #1481."""
    Event_Pydantic = pydantic_model_creator(Event, name="EventNullableTest")
    schema = Event_Pydantic.model_json_schema()

    # 'reporter' is a nullable FK (null=True) so it must NOT be required
    assert "reporter" not in schema["required"]
    reporter_prop = schema["properties"]["reporter"]
    assert reporter_prop.get("nullable") is True
    assert reporter_prop.get("default") is None

    # 'tournament' is a non-nullable FK so it MUST be required
    assert "tournament" in schema["required"]

    # 'address' is a nullable O2O backward relation so it must NOT be required
    assert "address" not in schema["required"]
    address_prop = schema["properties"]["address"]
    assert address_prop.get("nullable") is True
    assert address_prop.get("default") is None


def test_field_with_default_not_optional(db):
    """Fields with a default value but null=False should not be marked as Optional."""
    Event_Pydantic = pydantic_model_creator(Event, name="EventDefaultNotOptional")
    schema = Event_Pydantic.model_json_schema()

    # 'token' has default=generate_token but null is not set (defaults to False),
    # so it must NOT allow None values
    token_prop = schema["properties"]["token"]
    assert token_prop == {"title": "Token", "type": "string"}
    assert "anyOf" not in token_prop

    # Validation should reject None for a non-nullable field with a default
    with pytest.raises(ValidationError):
        Event_Pydantic(
            event_id=1, name="test", tournament=1, token=None, modified="2024-01-01T00:00:00"
        )


# Tests for computed fields accessing relations (#1440)
@pytest.mark.asyncio
async def test_computed_field_excluded_relation_not_prefetched(db):
    """Computed field accessing an excluded, non-prefetched relation.

    When team_members is excluded from the Pydantic model AND not manually prefetched,
    the wrapped function dispatches to the ORM object which raises NoValuesFetched.
    If the user's function handles the error gracefully (like team_size does),
    it returns a default. If it doesn't, NoValuesFetched propagates with a clear message.
    """
    Employee_Pydantic_NoTeam = pydantic_model_creator(
        Employee,
        name="Employee_NoTeam",
        exclude=("team_members", "manager", "gets_talked_to"),
        computed=("name_length", "team_size"),
        allow_cycles=True,
    )

    root = await Employee.create(name="Root")
    await Employee.create(name="Member1", manager=root)
    await Employee.create(name="Member2", manager=root)

    empp = await Employee_Pydantic_NoTeam.from_tortoise_orm(await Employee.get(name="Root"))
    empdict = empp.model_dump()

    assert "team_members" not in empdict
    # team_size returns 0 because team_members was not prefetched and the
    # team_size function gracefully handles NoValuesFetched
    assert empdict["team_size"] == 0
    assert empdict["name_length"] == 4


@pytest.mark.asyncio
async def test_computed_field_excluded_relation_works_with_manual_prefetch(db):
    """Computed field accessing an excluded relation works when manually prefetched.

    If the user prefetches the relation before calling from_tortoise_orm, the computed
    field can access it on the ORM object even though it's excluded from the schema.
    """
    Employee_Pydantic_NoTeam = pydantic_model_creator(
        Employee,
        name="Employee_NoTeam2",
        exclude=("team_members", "manager", "gets_talked_to"),
        computed=("name_length", "team_size"),
        allow_cycles=True,
    )

    root = await Employee.create(name="Root")
    await Employee.create(name="Member1", manager=root)
    await Employee.create(name="Member2", manager=root)

    obj = await Employee.get(name="Root")
    await obj.fetch_related("team_members")
    empp = await Employee_Pydantic_NoTeam.from_tortoise_orm(obj)
    empdict = empp.model_dump()

    assert "team_members" not in empdict
    assert empdict["team_size"] == 2
    assert empdict["name_length"] == 4


@pytest.mark.asyncio
async def test_computed_field_relation_in_model(db, pydantic_cycle_setup):
    """Computed field accessing a reverse relation that IS in the Pydantic model.

    This tests the happy path where team_members is a Pydantic field AND team_size
    accesses it via the ORM object.
    """
    Employee_Pydantic = pydantic_cycle_setup["Employee_Pydantic"]

    empp = await Employee_Pydantic.from_tortoise_orm(await Employee.get(name="Root"))
    empdict = empp.model_dump()

    # team_members is present in the schema
    assert "team_members" in empdict
    # team_size correctly reports the count
    assert empdict["team_size"] == 2
    assert empdict["name_length"] == 4
