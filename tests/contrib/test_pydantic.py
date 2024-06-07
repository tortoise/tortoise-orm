import copy

import pytest
from pydantic import ConfigDict, ValidationError

from tests.testmodels import (
    Address,
    CamelCaseAliasPerson,
    Employee,
    Event,
    JSONFields,
    Reporter,
    Team,
    Tournament,
    User,
)
from tortoise.contrib import test
from tortoise.contrib.pydantic import (
    PydanticModel,
    pydantic_model_creator,
    pydantic_queryset_creator,
)


class TestPydantic(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super(TestPydantic, self).asyncSetUp()
        self.Event_Pydantic = pydantic_model_creator(Event)
        self.Event_Pydantic_List = pydantic_queryset_creator(Event)
        self.Tournament_Pydantic = pydantic_model_creator(Tournament)
        self.Team_Pydantic = pydantic_model_creator(Team)
        self.Address_Pydantic = pydantic_model_creator(Address)

        class PydanticMetaOverride:
            backward_relations = False

        self.Event_Pydantic_non_backward = pydantic_model_creator(
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

    async def test_backward_relations(self):
        event_schema = copy.deepcopy(dict(self.Event_Pydantic.model_json_schema()))
        event_non_backward_schema = copy.deepcopy(
            dict(self.Event_Pydantic_non_backward.model_json_schema())
        )
        self.assertTrue("address" in event_schema["properties"])
        self.assertFalse("address" in event_non_backward_schema["properties"])
        del event_schema["properties"]["address"]
        self.assertEqual(event_schema["properties"], event_non_backward_schema["properties"])

    def test_event_schema(self):
        self.assertEqual(
            self.Event_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "event_id": {
                                "maximum": 9223372036854775807,
                                "minimum": -9223372036854775808,
                                "title": "Event Id",
                                "type": "integer",
                            },
                        },
                        "required": ["city", "street", "event_id"],
                        "title": "Address",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf": {
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
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf": {
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
                                "nullable": True,
                                "title": "Alias",
                            },
                        },
                        "required": ["id", "name", "alias"],
                        "title": "Team",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf": {
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
                        "required": ["id", "name", "desc", "created"],
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
                        "allOf": [
                            {
                                "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf"
                            }
                        ],
                        "description": "What tournaments is a happenin'",
                    },
                    "reporter": {
                        "anyOf": [
                            {
                                "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf"
                            },
                            {"type": "null"},
                        ],
                        "nullable": True,
                        "title": "Reporter",
                    },
                    "participants": {
                        "items": {
                            "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf"
                        },
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
                        "nullable": True,
                        "title": "Alias",
                    },
                    "address": {
                        "anyOf": [
                            {
                                "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf"
                            },
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
                    "alias",
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
                    "Event_ct5gv4": {
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
                                "allOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf"
                                    }
                                ],
                                "description": "What tournaments is a happenin'",
                            },
                            "reporter": {
                                "anyOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf"
                                    },
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Reporter",
                            },
                            "participants": {
                                "items": {
                                    "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf"
                                },
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
                                "nullable": True,
                                "title": "Alias",
                            },
                            "address": {
                                "anyOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf"
                                    },
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
                            "alias",
                            "address",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "event_id": {
                                "maximum": 9223372036854775807,
                                "minimum": -9223372036854775808,
                                "title": "Event Id",
                                "type": "integer",
                            },
                        },
                        "required": ["city", "street", "event_id"],
                        "title": "Address",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf": {
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
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf": {
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
                                "nullable": True,
                                "title": "Alias",
                            },
                        },
                        "required": ["id", "name", "alias"],
                        "title": "Team",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf": {
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
                        "required": ["id", "name", "desc", "created"],
                        "title": "Tournament",
                        "type": "object",
                    },
                },
                "description": "Events on the calendar",
                "items": {"$ref": "#/$defs/Event_ct5gv4"},
                "title": "Event_list",
                "type": "array",
            },
        )

    def test_address_schema(self):
        self.assertEqual(
            self.Address_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Event_aajoh6": {
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
                                "allOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf"
                                    }
                                ],
                                "description": "What tournaments is a happenin'",
                            },
                            "reporter": {
                                "anyOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf"
                                    },
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Reporter",
                            },
                            "participants": {
                                "items": {
                                    "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf"
                                },
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
                            "alias",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf": {
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
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf": {
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
                                "nullable": True,
                                "title": "Alias",
                            },
                        },
                        "required": ["id", "name", "alias"],
                        "title": "Team",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf": {
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
                        "required": ["id", "name", "desc", "created"],
                        "title": "Tournament",
                        "type": "object",
                    },
                },
                "additionalProperties": False,
                "properties": {
                    "city": {"maxLength": 64, "title": "City", "type": "string"},
                    "street": {"maxLength": 128, "title": "Street", "type": "string"},
                    "event": {"$ref": "#/$defs/Event_aajoh6"},
                    "event_id": {
                        "maximum": 9223372036854775807,
                        "minimum": -9223372036854775808,
                        "title": "Event Id",
                        "type": "integer",
                    },
                },
                "required": ["city", "street", "event", "event_id"],
                "title": "Address",
                "type": "object",
            },
        )

    def test_tournament_schema(self):
        self.assertEqual(
            self.Tournament_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Event_h4reuz": {
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
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf"
                                    },
                                    {"type": "null"},
                                ],
                                "nullable": True,
                                "title": "Reporter",
                            },
                            "participants": {
                                "items": {
                                    "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf"
                                },
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
                                "nullable": True,
                                "title": "Alias",
                            },
                            "address": {
                                "anyOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf"
                                    },
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
                            "alias",
                            "address",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "event_id": {
                                "maximum": 9223372036854775807,
                                "minimum": -9223372036854775808,
                                "title": "Event Id",
                                "type": "integer",
                            },
                        },
                        "required": ["city", "street", "event_id"],
                        "title": "Address",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf": {
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
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Team__leaf": {
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
                                "nullable": True,
                                "title": "Alias",
                            },
                        },
                        "required": ["id", "name", "alias"],
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
                        "items": {"$ref": "#/$defs/Event_h4reuz"},
                        "title": "Events",
                        "type": "array",
                    },
                },
                "required": ["id", "name", "desc", "created", "events"],
                "title": "Tournament",
                "type": "object",
            },
        )

    def test_team_schema(self):
        self.assertEqual(
            self.Team_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Event_mfn2l6": {
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
                                "allOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf"
                                    }
                                ],
                                "description": "What tournaments is a happenin'",
                            },
                            "reporter": {
                                "anyOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf"
                                    },
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
                                "nullable": True,
                                "title": "Alias",
                            },
                            "address": {
                                "anyOf": [
                                    {
                                        "$ref": "#/$defs/tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf"
                                    },
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
                            "alias",
                            "address",
                        ],
                        "title": "Event",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Address__leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "city": {"maxLength": 64, "title": "City", "type": "string"},
                            "street": {"maxLength": 128, "title": "Street", "type": "string"},
                            "event_id": {
                                "maximum": 9223372036854775807,
                                "minimum": -9223372036854775808,
                                "title": "Event Id",
                                "type": "integer",
                            },
                        },
                        "required": ["city", "street", "event_id"],
                        "title": "Address",
                        "type": "object",
                    },
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Reporter__leaf": {
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
                    "tortoise__contrib__pydantic__creator__tests__testmodels__Tournament__leaf": {
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
                        "required": ["id", "name", "desc", "created"],
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
                        "nullable": True,
                        "title": "Alias",
                    },
                    "events": {
                        "items": {"$ref": "#/$defs/Event_mfn2l6"},
                        "title": "Events",
                        "type": "array",
                    },
                },
                "required": ["id", "name", "alias", "events"],
                "title": "Team",
                "type": "object",
            },
        )

    async def test_eventlist(self):
        eventlp = await self.Event_Pydantic_List.from_queryset(Event.all())
        # print(eventlp.json(indent=4))
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
        # print(eventp.json(indent=4))
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
                "address": {"event_id": self.address.pk, "city": "Santa Monica", "street": "Ocean"},
            },
        )

    async def test_address(self):
        addressp = await self.Address_Pydantic.from_tortoise_orm(await Address.get(street="Ocean"))
        # print(addressp.json(indent=4))
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
            },
        )

    async def test_tournament(self):
        tournamentp = await self.Tournament_Pydantic.from_tortoise_orm(
            await Tournament.all().first()
        )
        # print(tournamentp.json(indent=4))
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
        # print(teamp.json(indent=4))
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

    def test_exclude_read_only(self):
        ModelPydantic = pydantic_model_creator(Event, exclude_readonly=True)

        self.assertNotIn("modified", ModelPydantic.model_json_schema()["properties"])


class TestPydanticCycle(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super(TestPydanticCycle, self).asyncSetUp()
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
                    "Employee_4fgkwn": {
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
                                "items": {"$ref": "#/$defs/leaf"},
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
                                "nullable": True,
                                "title": "Manager Id",
                            },
                            "team_members": {
                                "items": {"$ref": "#/$defs/leaf"},
                                "title": "Team Members",
                                "type": "array",
                            },
                        },
                        "required": ["id", "name", "talks_to", "manager_id", "team_members"],
                        "title": "Employee",
                        "type": "object",
                    },
                    "Employee_5gupxf": {
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
                                "items": {"$ref": "#/$defs/leaf"},
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
                                "nullable": True,
                                "title": "Manager Id",
                            },
                            "team_members": {
                                "items": {"$ref": "#/$defs/leaf"},
                                "title": "Team Members",
                                "type": "array",
                            },
                        },
                        "required": ["id", "name", "talks_to", "manager_id", "team_members"],
                        "title": "Employee",
                        "type": "object",
                    },
                    "leaf": {
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
                                "nullable": True,
                                "title": "Manager Id",
                            },
                        },
                        "required": ["id", "name", "manager_id"],
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
                        "items": {"$ref": "#/$defs/Employee_5gupxf"},
                        "title": "Talks To",
                        "type": "array",
                    },
                    "manager_id": {
                        "anyOf": [
                            {"maximum": 2147483647, "minimum": -2147483648, "type": "integer"},
                            {"type": "null"},
                        ],
                        "nullable": True,
                        "title": "Manager Id",
                    },
                    "team_members": {
                        "items": {"$ref": "#/$defs/Employee_4fgkwn"},
                        "title": "Team Members",
                        "type": "array",
                    },
                },
                "required": ["id", "name", "talks_to", "manager_id", "team_members"],
                "title": "Employee",
                "type": "object",
            },
        )

    async def test_serialisation(self):
        empp = await self.Employee_Pydantic.from_tortoise_orm(await Employee.get(name="Root"))
        # print(empp.json(indent=4))
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
