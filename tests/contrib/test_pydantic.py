import copy

import pytest
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
from tortoise.contrib import test
from tortoise.contrib.pydantic import (
    PydanticModel,
    pydantic_model_creator,
    pydantic_queryset_creator,
)


class TestPydantic(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.Event_Pydantic = pydantic_model_creator(Event)
        self.Event_Pydantic_List = pydantic_queryset_creator(Event)
        self.Tournament_Pydantic = pydantic_model_creator(Tournament)
        self.Team_Pydantic = pydantic_model_creator(Team)
        self.Address_Pydantic = pydantic_model_creator(Address)
        self.ModelTestPydanticMetaBackwardRelations1_Pydantic = pydantic_model_creator(
            ModelTestPydanticMetaBackwardRelations1
        )
        self.ModelTestPydanticMetaBackwardRelations2_Pydantic = pydantic_model_creator(
            ModelTestPydanticMetaBackwardRelations2
        )

        class PydanticMetaOverride:
            backward_relations = False

        self.Event_Pydantic_non_backward_from_override = pydantic_model_creator(
            Event, meta_override=PydanticMetaOverride, name="Event_non_backward"
        )

        self.tournament = await Tournament.create(name="New Tournament")
        self.reporter = await Reporter.create(name="The Reporter")
        self.event = await Event.create(
            name="Test", tournament=self.tournament, reporter=self.reporter
        )
        self.event2 = await Event.create(name="Test2", tournament=self.tournament)
        self.address = await Address.create(city="Santa Monica", street="Ocean", event=self.event)
        self.team1 = await Team.create(name="Onesies")
        self.team2 = await Team.create(name="T-Shirts")
        await self.event.participants.add(self.team1, self.team2)
        await self.event2.participants.add(self.team1, self.team2)
        self.maxDiff = None

    async def test_backward_relations_with_meta_override(self):
        event_schema = copy.deepcopy(dict(self.Event_Pydantic.model_json_schema()))
        event_non_backward_schema_by_override = copy.deepcopy(
            dict(self.Event_Pydantic_non_backward_from_override.model_json_schema())
        )
        self.assertTrue("address" in event_schema["properties"])
        self.assertFalse("address" in event_non_backward_schema_by_override["properties"])
        del event_schema["properties"]["address"]
        self.assertEqual(
            event_schema["properties"], event_non_backward_schema_by_override["properties"]
        )

    async def test_backward_relations_with_pydantic_meta(self):
        test_model1_schema = (
            self.ModelTestPydanticMetaBackwardRelations1_Pydantic.model_json_schema()
        )
        test_model2_schema = (
            self.ModelTestPydanticMetaBackwardRelations2_Pydantic.model_json_schema()
        )
        self.assertTrue("threes" in test_model2_schema["properties"])
        self.assertFalse("threes" in test_model1_schema["properties"])
        del test_model2_schema["properties"]["threes"]
        self.assertEqual(test_model2_schema["properties"], test_model1_schema["properties"])
        print(test_model2_schema)

    def test_event_schema(self):
        self.assertEqual(
            self.Event_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Address_e4rhju_leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "m2mwitho2opks": {
                                "items": {"$ref": "#/$defs/M2mWithO2oPk_leajz6_leaf"},
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
                    "M2mWithO2oPk_leajz6_leaf": {
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
                    "Reporter_fgnv33_leaf": {
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
                    "Team_ip4pg6_leaf": {
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
                    "Tournament_5y7e7j_leaf": {
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
                        "$ref": "#/$defs/Tournament_5y7e7j_leaf",
                        "description": "What tournaments is a happenin'",
                    },
                    "reporter": {
                        "anyOf": [
                            {"$ref": "#/$defs/Reporter_fgnv33_leaf"},
                            {"type": "null"},
                        ],
                        "nullable": True,
                        "title": "Reporter",
                    },
                    "participants": {
                        "items": {"$ref": "#/$defs/Team_ip4pg6_leaf"},
                        "title": "Participants",
                        "type": "array",
                    },
                    "modified": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Modified",
                        "type": "string",
                    },
                    "token": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Token"},
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
                            {"$ref": "#/$defs/Address_e4rhju_leaf"},
                            {"type": "null"},
                        ],
                        "nullable": True,
                        "title": "Address",
                    },
                },
                "required": [
                    "event_id",
                    "name",
                    "tournament",
                    "reporter",
                    "participants",
                    "modified",
                    "token",
                    "address",
                ],
                "title": "Event",
                "type": "object",
            },
        )

    def test_eventlist_schema(self):
        self.assertEqual(
            self.Event_Pydantic_List.model_json_schema(),
            {
                "$defs": {
                    "Event_mfxmwb": {
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
                                "$ref": "#/$defs/Tournament_5y7e7j_leaf",
                                "description": "What tournaments is a happenin'",
                            },
                            "reporter": {
                                "anyOf": [
                                    {"$ref": "#/$defs/Reporter_fgnv33_leaf"},
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Reporter",
                            },
                            "participants": {
                                "items": {"$ref": "#/$defs/Team_ip4pg6_leaf"},
                                "title": "Participants",
                                "type": "array",
                            },
                            "modified": {
                                "format": "date-time",
                                "readOnly": True,
                                "title": "Modified",
                                "type": "string",
                            },
                            "token": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "title": "Token",
                            },
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
                                    {"$ref": "#/$defs/Address_e4rhju_leaf"},
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Address",
                            },
                        },
                        "required": [
                            "event_id",
                            "name",
                            "tournament",
                            "reporter",
                            "participants",
                            "modified",
                            "token",
                            "address",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "Address_e4rhju_leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "m2mwitho2opks": {
                                "items": {"$ref": "#/$defs/M2mWithO2oPk_leajz6_leaf"},
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
                    "M2mWithO2oPk_leajz6_leaf": {
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
                    "Reporter_fgnv33_leaf": {
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
                    "Team_ip4pg6_leaf": {
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
                    "Tournament_5y7e7j_leaf": {
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
                "items": {"$ref": "#/$defs/Event_mfxmwb"},
                "title": "Event_list",
                "type": "array",
            },
        )

    def test_address_schema(self):
        self.assertEqual(
            self.Address_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Event_zvunzw_leaf": {
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
                                "$ref": "#/$defs/Tournament_5y7e7j_leaf",
                                "description": "What tournaments is a happenin'",
                            },
                            "reporter": {
                                "anyOf": [
                                    {"$ref": "#/$defs/Reporter_fgnv33_leaf"},
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Reporter",
                            },
                            "participants": {
                                "items": {"$ref": "#/$defs/Team_ip4pg6_leaf"},
                                "title": "Participants",
                                "type": "array",
                            },
                            "modified": {
                                "format": "date-time",
                                "readOnly": True,
                                "title": "Modified",
                                "type": "string",
                            },
                            "token": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "title": "Token",
                            },
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
                            "reporter",
                            "participants",
                            "modified",
                            "token",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "M2mWithO2oPk_leajz6_leaf": {
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
                    "Reporter_fgnv33_leaf": {
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
                    "Team_ip4pg6_leaf": {
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
                    "Tournament_5y7e7j_leaf": {
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
                        "items": {"$ref": "#/$defs/M2mWithO2oPk_leajz6_leaf"},
                        "title": "M2Mwitho2Opks",
                        "type": "array",
                    },
                    "event": {"$ref": "#/$defs/Event_zvunzw_leaf"},
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
            },
        )

    def test_tournament_schema(self):
        self.assertEqual(
            self.Tournament_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Event_ln6p2q_leaf": {
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
                                    {"$ref": "#/$defs/Reporter_fgnv33_leaf"},
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Reporter",
                            },
                            "participants": {
                                "items": {"$ref": "#/$defs/Team_ip4pg6_leaf"},
                                "title": "Participants",
                                "type": "array",
                            },
                            "modified": {
                                "format": "date-time",
                                "readOnly": True,
                                "title": "Modified",
                                "type": "string",
                            },
                            "token": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "title": "Token",
                            },
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
                                    {"$ref": "#/$defs/Address_e4rhju_leaf"},
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Address",
                            },
                        },
                        "required": [
                            "event_id",
                            "name",
                            "reporter",
                            "participants",
                            "modified",
                            "token",
                            "address",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "Address_e4rhju_leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "m2mwitho2opks": {
                                "items": {"$ref": "#/$defs/M2mWithO2oPk_leajz6_leaf"},
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
                    "M2mWithO2oPk_leajz6_leaf": {
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
                    "Reporter_fgnv33_leaf": {
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
                    "Team_ip4pg6_leaf": {
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
                        "items": {"$ref": "#/$defs/Event_ln6p2q_leaf"},
                        "title": "Events",
                        "type": "array",
                    },
                },
                "required": ["id", "name", "created", "events"],
                "title": "Tournament",
                "type": "object",
            },
        )

    def test_team_schema(self):
        self.assertEqual(
            self.Team_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Event_lfs4vy_leaf": {
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
                                "$ref": "#/$defs/Tournament_5y7e7j_leaf",
                                "description": "What tournaments is a happenin'",
                            },
                            "reporter": {
                                "anyOf": [
                                    {"$ref": "#/$defs/Reporter_fgnv33_leaf"},
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Reporter",
                            },
                            "modified": {
                                "format": "date-time",
                                "readOnly": True,
                                "title": "Modified",
                                "type": "string",
                            },
                            "token": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "title": "Token",
                            },
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
                                    {"$ref": "#/$defs/Address_e4rhju_leaf"},
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Address",
                            },
                        },
                        "required": [
                            "event_id",
                            "name",
                            "tournament",
                            "reporter",
                            "modified",
                            "token",
                            "address",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "Address_e4rhju_leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "m2mwitho2opks": {
                                "items": {"$ref": "#/$defs/M2mWithO2oPk_leajz6_leaf"},
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
                    "M2mWithO2oPk_leajz6_leaf": {
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
                    "Reporter_fgnv33_leaf": {
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
                    "Tournament_5y7e7j_leaf": {
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
                        "items": {"$ref": "#/$defs/Event_lfs4vy_leaf"},
                        "title": "Events",
                        "type": "array",
                    },
                },
                "required": ["id", "name", "events"],
                "title": "Team",
                "type": "object",
            },
        )

    async def test_eventlist(self):
        eventlp = await self.Event_Pydantic_List.from_queryset(Event.all())
        eventldict = eventlp.model_dump()

        # Remove timestamps
        del eventldict[0]["modified"]
        del eventldict[0]["tournament"]["created"]
        del eventldict[1]["modified"]
        del eventldict[1]["tournament"]["created"]

        self.assertEqual(
            eventldict,
            [
                {
                    "event_id": self.event.event_id,
                    "name": "Test",
                    # "modified": "2020-01-28T10:43:50.901562",
                    "token": self.event.token,
                    "alias": None,
                    "tournament": {
                        "id": self.tournament.id,
                        "name": "New Tournament",
                        "desc": None,
                        # "created": "2020-01-28T10:43:50.900664"
                    },
                    "reporter": {"id": self.reporter.id, "name": "The Reporter"},
                    "participants": [
                        {"id": self.team1.id, "name": "Onesies", "alias": None},
                        {"id": self.team2.id, "name": "T-Shirts", "alias": None},
                    ],
                    "address": {
                        "event_id": self.address.pk,
                        "city": "Santa Monica",
                        "m2mwitho2opks": [],
                        "street": "Ocean",
                    },
                },
                {
                    "event_id": self.event2.event_id,
                    "name": "Test2",
                    # "modified": "2020-01-28T10:43:50.901562",
                    "token": self.event2.token,
                    "alias": None,
                    "tournament": {
                        "id": self.tournament.id,
                        "name": "New Tournament",
                        "desc": None,
                        # "created": "2020-01-28T10:43:50.900664"
                    },
                    "reporter": None,
                    "participants": [
                        {"id": self.team1.id, "name": "Onesies", "alias": None},
                        {"id": self.team2.id, "name": "T-Shirts", "alias": None},
                    ],
                    "address": None,
                },
            ],
        )

    async def test_event(self):
        eventp = await self.Event_Pydantic.from_tortoise_orm(await Event.get(name="Test"))
        eventdict = eventp.model_dump()

        # Remove timestamps
        del eventdict["modified"]
        del eventdict["tournament"]["created"]

        self.assertEqual(
            eventdict,
            {
                "event_id": self.event.event_id,
                "name": "Test",
                # "modified": "2020-01-28T10:43:50.901562",
                "token": self.event.token,
                "alias": None,
                "tournament": {
                    "id": self.tournament.id,
                    "name": "New Tournament",
                    "desc": None,
                    # "created": "2020-01-28T10:43:50.900664"
                },
                "reporter": {"id": self.reporter.id, "name": "The Reporter"},
                "participants": [
                    {"id": self.team1.id, "name": "Onesies", "alias": None},
                    {"id": self.team2.id, "name": "T-Shirts", "alias": None},
                ],
                "address": {
                    "event_id": self.address.pk,
                    "city": "Santa Monica",
                    "m2mwitho2opks": [],
                    "street": "Ocean",
                },
            },
        )

    async def test_address(self):
        addressp = await self.Address_Pydantic.from_tortoise_orm(await Address.get(street="Ocean"))
        addressdict = addressp.model_dump()

        # Remove timestamps
        del addressdict["event"]["tournament"]["created"]
        del addressdict["event"]["modified"]

        self.assertEqual(
            addressdict,
            {
                "city": "Santa Monica",
                "street": "Ocean",
                "event": {
                    "event_id": self.event.event_id,
                    "name": "Test",
                    "tournament": {
                        "id": self.tournament.id,
                        "name": "New Tournament",
                        "desc": None,
                    },
                    "reporter": {"id": self.reporter.id, "name": "The Reporter"},
                    "participants": [
                        {"id": self.team1.id, "name": "Onesies", "alias": None},
                        {"id": self.team2.id, "name": "T-Shirts", "alias": None},
                    ],
                    "token": self.event.token,
                    "alias": None,
                },
                "event_id": self.address.event_id,
                "m2mwitho2opks": [],
            },
        )

    async def test_tournament(self):
        tournamentp = await self.Tournament_Pydantic.from_tortoise_orm(
            await Tournament.all().first()
        )
        tournamentdict = tournamentp.model_dump()

        # Remove timestamps
        del tournamentdict["events"][0]["modified"]
        del tournamentdict["events"][1]["modified"]
        del tournamentdict["created"]

        self.assertEqual(
            tournamentdict,
            {
                "id": self.tournament.id,
                "name": "New Tournament",
                "desc": None,
                # "created": "2020-01-28T19:41:38.059617",
                "events": [
                    {
                        "event_id": self.event.event_id,
                        "name": "Test",
                        # "modified": "2020-01-28T19:41:38.060070",
                        "token": self.event.token,
                        "alias": None,
                        "reporter": {"id": self.reporter.id, "name": "The Reporter"},
                        "participants": [
                            {"id": self.team1.id, "name": "Onesies", "alias": None},
                            {"id": self.team2.id, "name": "T-Shirts", "alias": None},
                        ],
                        "address": {
                            "event_id": self.address.pk,
                            "city": "Santa Monica",
                            "m2mwitho2opks": [],
                            "street": "Ocean",
                        },
                    },
                    {
                        "event_id": self.event2.event_id,
                        "name": "Test2",
                        # "modified": "2020-01-28T19:41:38.060070",
                        "token": self.event2.token,
                        "alias": None,
                        "reporter": None,
                        "participants": [
                            {"id": self.team1.id, "name": "Onesies", "alias": None},
                            {"id": self.team2.id, "name": "T-Shirts", "alias": None},
                        ],
                        "address": None,
                    },
                ],
            },
        )

    async def test_team(self):
        teamp = await self.Team_Pydantic.from_tortoise_orm(await Team.get(id=self.team1.id))
        teamdict = teamp.model_dump()

        # Remove timestamps
        del teamdict["events"][0]["modified"]
        del teamdict["events"][0]["tournament"]["created"]
        del teamdict["events"][1]["modified"]
        del teamdict["events"][1]["tournament"]["created"]

        self.assertEqual(
            teamdict,
            {
                "id": self.team1.id,
                "name": "Onesies",
                "alias": None,
                "events": [
                    {
                        "event_id": self.event.event_id,
                        "name": "Test",
                        # "modified": "2020-01-28T19:47:03.334077",
                        "token": self.event.token,
                        "alias": None,
                        "tournament": {
                            "id": self.tournament.id,
                            "name": "New Tournament",
                            "desc": None,
                            # "created": "2020-01-28T19:41:38.059617",
                        },
                        "reporter": {"id": self.reporter.id, "name": "The Reporter"},
                        "address": {
                            "event_id": self.address.pk,
                            "city": "Santa Monica",
                            "m2mwitho2opks": [],
                            "street": "Ocean",
                        },
                    },
                    {
                        "event_id": self.event2.event_id,
                        "name": "Test2",
                        # "modified": "2020-01-28T19:47:03.334077",
                        "token": self.event2.token,
                        "alias": None,
                        "tournament": {
                            "id": self.tournament.id,
                            "name": "New Tournament",
                            "desc": None,
                            # "created": "2020-01-28T19:41:38.059617",
                        },
                        "reporter": None,
                        "address": None,
                    },
                ],
            },
        )

    def test_event_named(self):
        Event_Named = pydantic_model_creator(Event, name="Foo")
        schema = Event_Named.model_json_schema()
        self.assertEqual(schema["title"], "Foo")
        self.assertSetEqual(
            set(schema["properties"].keys()),
            {
                "address",
                "alias",
                "event_id",
                "modified",
                "name",
                "participants",
                "reporter",
                "token",
                "tournament",
            },
        )

    def test_event_sorted(self):
        Event_Named = pydantic_model_creator(Event, sort_alphabetically=True)
        schema = Event_Named.model_json_schema()
        self.assertEqual(
            list(schema["properties"].keys()),
            [
                "address",
                "alias",
                "event_id",
                "modified",
                "name",
                "participants",
                "reporter",
                "token",
                "tournament",
            ],
        )

    def test_event_unsorted(self):
        Event_Named = pydantic_model_creator(Event, sort_alphabetically=False)
        schema = Event_Named.model_json_schema()
        self.assertEqual(
            list(schema["properties"].keys()),
            [
                "event_id",
                "name",
                "tournament",
                "reporter",
                "participants",
                "modified",
                "token",
                "alias",
                "address",
            ],
        )

    async def test_json_field(self):
        json_field_0 = await JSONFields.create(data={"a": 1})
        json_field_1 = await JSONFields.create(data=[{"a": 1, "b": 2}])
        json_field_0_get = await JSONFields.get(pk=json_field_0.pk)
        json_field_1_get = await JSONFields.get(pk=json_field_1.pk)

        creator = pydantic_model_creator(JSONFields)
        ret0 = creator.model_validate(json_field_0_get).model_dump()
        self.assertEqual(
            ret0,
            {
                "id": json_field_0.pk,
                "data": {"a": 1},
                "data_null": None,
                "data_default": {"a": 1},
                "data_validate": None,
                "data_pydantic": json_pydantic_default.model_dump(),
            },
        )
        ret1 = creator.model_validate(json_field_1_get).model_dump()
        self.assertEqual(
            ret1,
            {
                "id": json_field_1.pk,
                "data": [{"a": 1, "b": 2}],
                "data_null": None,
                "data_default": {"a": 1},
                "data_validate": None,
                "data_pydantic": json_pydantic_default.model_dump(),
            },
        )

    def test_override_default_model_config_by_config_class(self):
        """Pydantic meta's config_class should be able to override default config."""
        CamelCaseAliasPersonCopy = copy.deepcopy(CamelCaseAliasPerson)
        # Set class pydantic config's orm_mode to False
        CamelCaseAliasPersonCopy.PydanticMeta.model_config["from_attributes"] = False

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson, name="AutoAliasPersonOverriddenORMMode"
        )

        self.assertEqual(ModelPydantic.model_config["from_attributes"], False)

    def test_override_meta_pydantic_config_by_model_creator(self):
        model_config = ConfigDict(title="Another title!")

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson,
            model_config=model_config,
            name="AutoAliasPersonModelCreatorConfig",
        )

        self.assertEqual(model_config["title"], ModelPydantic.model_config["title"])

    def test_config_classes_merge_all_configs(self):
        """Model creator should merge all 3 configs.

        - It merges (Default, Meta's config_class and creator's config_class) together.
        """
        model_config = ConfigDict(str_min_length=3)

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson, name="AutoAliasPersonMinLength", model_config=model_config
        )

        # Should set min_anystr_length from pydantic_model_creator's config
        self.assertEqual(
            ModelPydantic.model_config["str_min_length"], model_config["str_min_length"]
        )
        # Should set title from model PydanticMeta's config
        self.assertEqual(
            ModelPydantic.model_config["title"],
            CamelCaseAliasPerson.PydanticMeta.model_config["title"],
        )
        # Should set orm_mode from base pydantic model configuration
        self.assertEqual(
            ModelPydantic.model_config["from_attributes"],
            PydanticModel.model_config["from_attributes"],
        )

    def test_exclude_readonly(self):
        ModelPydantic = pydantic_model_creator(Event, exclude_readonly=True)

        self.assertNotIn("modified", ModelPydantic.model_json_schema()["properties"])


class TestPydanticCycle(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.Employee_Pydantic = pydantic_model_creator(Employee)

        self.root = await Employee.create(name="Root")
        self.loose = await Employee.create(name="Loose")
        self._1 = await Employee.create(name="1. First H1", manager=self.root)
        self._2 = await Employee.create(name="2. Second H1", manager=self.root)
        self._1_1 = await Employee.create(name="1.1. First H2", manager=self._1)
        self._1_1_1 = await Employee.create(name="1.1.1. First H3", manager=self._1_1)
        self._2_1 = await Employee.create(name="2.1. Second H2", manager=self._2)
        self._2_2 = await Employee.create(name="2.2. Third H2", manager=self._2)

        await self._1.talks_to.add(self._2, self._1_1_1, self.loose)
        await self._2_1.gets_talked_to.add(self._2_2, self._1_1, self.loose)
        self.maxDiff = None

    def test_schema(self):
        self.assertEqual(
            self.Employee_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Employee_6tkbjb_leaf": {
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
                                "items": {"$ref": "#/$defs/Employee_fj2ly4_leaf"},
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
                                "items": {"$ref": "#/$defs/Employee_fj2ly4_leaf"},
                                "title": "Team Members",
                                "type": "array",
                            },
                        },
                        "required": ["id", "name", "talks_to", "team_members"],
                        "title": "Employee",
                        "type": "object",
                    },
                    "Employee_fj2ly4_leaf": {
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
                        "items": {"$ref": "#/$defs/Employee_6tkbjb_leaf"},
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
                        "items": {"$ref": "#/$defs/Employee_6tkbjb_leaf"},
                        "title": "Team Members",
                        "type": "array",
                    },
                },
                "required": ["id", "name", "talks_to", "team_members"],
                "title": "Employee",
                "type": "object",
            },
        )

    async def test_serialisation(self):
        empp = await self.Employee_Pydantic.from_tortoise_orm(await Employee.get(name="Root"))
        empdict = empp.model_dump()

        self.assertEqual(
            empdict,
            {
                "id": self.root.id,
                "manager_id": None,
                "name": "Root",
                "talks_to": [],
                "team_members": [
                    {
                        "id": self._1.id,
                        "manager_id": self.root.id,
                        "name": "1. First H1",
                        "talks_to": [
                            {
                                "id": self.loose.id,
                                "manager_id": None,
                                "name": "Loose",
                                "name_length": 5,
                                "team_size": 0,
                            },
                            {
                                "id": self._2.id,
                                "manager_id": self.root.id,
                                "name": "2. Second H1",
                                "name_length": 12,
                                "team_size": 0,
                            },
                            {
                                "id": self._1_1_1.id,
                                "manager_id": self._1_1.id,
                                "name": "1.1.1. First H3",
                                "name_length": 15,
                                "team_size": 0,
                            },
                        ],
                        "team_members": [
                            {
                                "id": self._1_1.id,
                                "manager_id": self._1.id,
                                "name": "1.1. First H2",
                                "name_length": 13,
                                "team_size": 0,
                            }
                        ],
                        "name_length": 11,
                        "team_size": 1,
                    },
                    {
                        "id": self._2.id,
                        "manager_id": self.root.id,
                        "name": "2. Second H1",
                        "talks_to": [],
                        "team_members": [
                            {
                                "id": self._2_1.id,
                                "manager_id": self._2.id,
                                "name": "2.1. Second H2",
                                "name_length": 14,
                                "team_size": 0,
                            },
                            {
                                "id": self._2_2.id,
                                "manager_id": self._2.id,
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
            },
        )


class TestPydanticComputed(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.Employee_Pydantic = pydantic_model_creator(Employee)
        self.employee = await Employee.create(name="Some Employee")
        self.maxDiff = None

    async def test_computed_field(self):
        employee_pyd = await self.Employee_Pydantic.from_tortoise_orm(
            await Employee.get(name="Some Employee")
        )
        employee_serialised = employee_pyd.model_dump()
        self.assertEqual(employee_serialised.get("name_length"), self.employee.name_length())

    async def test_computed_field_schema(self):
        self.assertEqual(
            self.Employee_Pydantic.model_json_schema(mode="serialization"),
            {
                "$defs": {
                    "Employee_fj2ly4_leaf": {
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
                    "Employee_6tkbjb_leaf": {
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
                                "items": {"$ref": "#/$defs/Employee_fj2ly4_leaf"},
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
                                "items": {"$ref": "#/$defs/Employee_fj2ly4_leaf"},
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
                        "items": {"$ref": "#/$defs/Employee_6tkbjb_leaf"},
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
                        "items": {"$ref": "#/$defs/Employee_6tkbjb_leaf"},
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
            },
        )


class TestPydanticUpdate(test.TestCase):
    def setUp(self) -> None:
        self.UserCreate_Pydantic = pydantic_model_creator(
            User,
            name="UserCreate",
            exclude_readonly=True,
        )
        self.UserUpdate_Pydantic = pydantic_model_creator(
            User,
            name="UserUpdate",
            exclude_readonly=True,
            optional=("username", "mail", "bio"),
        )

    def test_create_schema(self):
        self.assertEqual(
            self.UserCreate_Pydantic.model_json_schema(),
            {
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
            },
        )

    def test_update_schema(self):
        """All fields of this schema should be optional.
        This demonstrates an example PATCH endpoint in an API, where a client may want
        to update a single field of a model without modifying the rest.
        """
        self.assertEqual(
            self.UserUpdate_Pydantic.model_json_schema(),
            {
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
            },
        )


class TestPydanticOptionalUpdate(test.TestCase):
    def setUp(self) -> None:
        self.UserUpdateAllOptional_Pydantic = pydantic_model_creator(
            User,
            name="UserUpdateAllOptional",
            exclude_readonly=True,
            optional=("username", "mail", "bio"),
        )
        self.UserUpdatePartialOptional_Pydantic = pydantic_model_creator(
            User,
            name="UserUpdatePartialOptional",
            exclude_readonly=True,
            optional=("username", "mail"),
        )
        self.UserUpdateWithoutOptional_Pydantic = pydantic_model_creator(
            User,
            name="UserUpdateWithoutOptional",
            exclude_readonly=True,
        )

    def test_optional_update(self):
        # All fields are optional
        self.assertEqual(self.UserUpdateAllOptional_Pydantic().model_dump(exclude_unset=True), {})
        self.assertEqual(
            self.UserUpdateAllOptional_Pydantic(bio="foo").model_dump(exclude_unset=True),
            {"bio": "foo"},
        )
        self.assertEqual(
            self.UserUpdateAllOptional_Pydantic(username="name", mail="a@example.com").model_dump(
                exclude_unset=True
            ),
            {"username": "name", "mail": "a@example.com"},
        )
        self.assertEqual(
            self.UserUpdateAllOptional_Pydantic(username="name", mail="a@example.com").model_dump(),
            {"username": "name", "mail": "a@example.com", "bio": None},
        )
        # Some fields are optional
        with pytest.raises(ValidationError):
            self.UserUpdatePartialOptional_Pydantic()
        with pytest.raises(ValidationError):
            self.UserUpdatePartialOptional_Pydantic(username="name")
        self.assertEqual(
            self.UserUpdatePartialOptional_Pydantic(bio="foo").model_dump(exclude_unset=True),
            {"bio": "foo"},
        )
        self.assertEqual(
            self.UserUpdatePartialOptional_Pydantic(
                username="name", mail="a@example.com", bio=""
            ).model_dump(exclude_unset=True),
            {"username": "name", "mail": "a@example.com", "bio": ""},
        )
        self.assertEqual(
            self.UserUpdatePartialOptional_Pydantic(mail="a@example.com", bio="").model_dump(),
            {"username": None, "mail": "a@example.com", "bio": ""},
        )
        # None of the fields is optional
        with pytest.raises(ValidationError):
            self.UserUpdateWithoutOptional_Pydantic()
        with pytest.raises(ValidationError):
            self.UserUpdateWithoutOptional_Pydantic(username="name")
        with pytest.raises(ValidationError):
            self.UserUpdateWithoutOptional_Pydantic(username="name", email="")
        self.assertEqual(
            self.UserUpdateWithoutOptional_Pydantic(
                username="name", mail="a@example.com", bio=""
            ).model_dump(),
            {"username": "name", "mail": "a@example.com", "bio": ""},
        )


class TestPydanticMutlipleModelUses(test.TestCase):
    def setUp(self) -> None:
        self.NoRelationsModel = IntFields
        self.ModelWithRelations = Event

    def test_no_relations_model_reused(self):
        Pydantic1 = pydantic_model_creator(self.NoRelationsModel)
        Pydantic2 = pydantic_model_creator(self.NoRelationsModel)

        self.assertIs(Pydantic1, Pydantic2)

    def test_no_relations_model_one_exclude(self):
        Pydantic1 = pydantic_model_creator(self.NoRelationsModel)
        Pydantic2 = pydantic_model_creator(self.NoRelationsModel, exclude=("id",))

        self.assertIsNot(Pydantic1, Pydantic2)
        self.assertIn("id", Pydantic1.model_json_schema()["required"])
        self.assertNotIn("id", Pydantic2.model_json_schema()["required"])

    def test_no_relations_model_both_exclude(self):
        Pydantic1 = pydantic_model_creator(self.NoRelationsModel, exclude=("id",))
        Pydantic2 = pydantic_model_creator(self.NoRelationsModel, exclude=("id",))

        self.assertIs(Pydantic1, Pydantic2)
        self.assertNotIn("id", Pydantic1.model_json_schema()["required"])
        self.assertNotIn("id", Pydantic2.model_json_schema()["required"])

    def test_no_relations_model_exclude_diff(self):
        Pydantic1 = pydantic_model_creator(self.NoRelationsModel, exclude=("id",))
        Pydantic2 = pydantic_model_creator(self.NoRelationsModel, exclude=("name",))

        self.assertIsNot(Pydantic1, Pydantic2)

    def test_no_relations_model_exclude_readonly(self):
        Pydantic1 = pydantic_model_creator(self.NoRelationsModel)
        Pydantic2 = pydantic_model_creator(self.NoRelationsModel, exclude_readonly=True)

        self.assertIsNot(Pydantic1, Pydantic2)
        self.assertIn("id", Pydantic1.model_json_schema()["properties"])
        self.assertNotIn("id", Pydantic2.model_json_schema()["properties"])

    def test_model_with_relations_reused(self):
        Pydantic1 = pydantic_model_creator(self.ModelWithRelations)
        Pydantic2 = pydantic_model_creator(self.ModelWithRelations)

        self.assertIs(Pydantic1, Pydantic2)

    def test_model_with_relations_exclude(self):
        Pydantic1 = pydantic_model_creator(self.ModelWithRelations)
        Pydantic2 = pydantic_model_creator(self.ModelWithRelations, exclude=("event_id",))

        self.assertIsNot(Pydantic1, Pydantic2)
        self.assertIn("event_id", Pydantic1.model_json_schema()["properties"])
        self.assertNotIn("event_id", Pydantic2.model_json_schema()["properties"])

    def test_model_with_relations_exclude_readonly(self):
        Pydantic1 = pydantic_model_creator(self.ModelWithRelations)
        Pydantic2 = pydantic_model_creator(self.ModelWithRelations, exclude_readonly=True)

        self.assertIsNot(Pydantic1, Pydantic2)
        self.assertIn("event_id", Pydantic1.model_json_schema()["properties"])
        self.assertNotIn("event_id", Pydantic2.model_json_schema()["properties"])

    def test_named_no_relations_model(self):
        Pydantic1 = pydantic_model_creator(self.NoRelationsModel, name="Foo")
        Pydantic2 = pydantic_model_creator(self.NoRelationsModel, name="Foo")

        self.assertIs(Pydantic1, Pydantic2)

    def test_named_model_with_relations(self):
        Pydantic1 = pydantic_model_creator(self.ModelWithRelations, name="Foo")
        Pydantic2 = pydantic_model_creator(self.ModelWithRelations, name="Foo")

        self.assertIs(Pydantic1, Pydantic2)


class TestPydanticEnum(test.TestCase):
    def setUp(self) -> None:
        self.EnumFields_Pydantic = pydantic_model_creator(EnumFields)

    def test_int_enum(self):
        with self.assertRaises(ValidationError) as cm:
            self.EnumFields_Pydantic.model_validate({"id": 1, "service": 4, "currency": "HUF"})
        self.assertEqual(
            [
                {
                    "type": "enum",
                    "loc": ("service",),
                    "msg": "Input should be 1, 2 or 3",
                    "input": 4,
                    "ctx": {"expected": "1, 2 or 3"},
                }
            ],
            cm.exception.errors(include_url=False),
        )
        with self.assertRaises(ValidationError) as cm:
            self.EnumFields_Pydantic.model_validate(
                {"id": 1, "service": "a string, not int", "currency": "HUF"}
            )
        self.assertEqual(
            [
                {
                    "type": "enum",
                    "loc": ("service",),
                    "msg": "Input should be 1, 2 or 3",
                    "input": "a string, not int",
                    "ctx": {"expected": "1, 2 or 3"},
                }
            ],
            cm.exception.errors(include_url=False),
        )

    def test_str_enum(self):
        with self.assertRaises(ValidationError) as cm:
            self.EnumFields_Pydantic.model_validate(
                {"id": 1, "service": 3, "currency": "GoofyGooberDollar"}
            )
        self.assertEqual(
            [
                {
                    "type": "enum",
                    "loc": ("currency",),
                    "msg": "Input should be 'HUF', 'EUR' or 'USD'",
                    "input": "GoofyGooberDollar",
                    "ctx": {"expected": "'HUF', 'EUR' or 'USD'"},
                }
            ],
            cm.exception.errors(include_url=False),
        )
        with self.assertRaises(ValidationError) as cm:
            self.EnumFields_Pydantic.model_validate({"id": 1, "service": 3, "currency": 1})
        self.assertEqual(
            [
                {
                    "type": "enum",
                    "loc": ("currency",),
                    "msg": "Input should be 'HUF', 'EUR' or 'USD'",
                    "input": 1,
                    "ctx": {"expected": "'HUF', 'EUR' or 'USD'"},
                }
            ],
            cm.exception.errors(include_url=False),
        )

    def test_enum(self):
        with self.assertRaises(ValidationError) as cm:
            self.EnumFields_Pydantic.model_validate({"id": 1, "service": 4, "currency": 1})
        self.assertEqual(
            [
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
            ],
            cm.exception.errors(include_url=False),
        )

        # should simply not raise any error:
        self.EnumFields_Pydantic.model_validate({"id": 1, "service": 3, "currency": "HUF"})
        self.assertEqual(
            {
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
            },
            self.EnumFields_Pydantic.model_json_schema(),
        )
