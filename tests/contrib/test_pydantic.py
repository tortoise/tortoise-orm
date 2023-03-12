import copy

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

from pydantic import BaseConfig as PydanticBaseConfig


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
        event_schema = copy.deepcopy(dict(self.Event_Pydantic.schema()))
        event_non_backward_schema = copy.deepcopy(dict(self.Event_Pydantic_non_backward.schema()))
        self.assertTrue("address" in event_schema["properties"])
        self.assertFalse("address" in event_non_backward_schema["properties"])
        del event_schema["properties"]["address"]
        self.assertEqual(event_schema["properties"], event_non_backward_schema["properties"])

    def test_event_schema(self):
        self.assertEqual(
            self.Event_Pydantic.schema(),
            {
                "title": "Event",
                "description": "Events on the calendar",
                "type": "object",
                "properties": {
                    "event_id": {
                        "title": "Event Id",
                        "minimum": 1,
                        "maximum": 9223372036854775807,
                        "type": "integer",
                    },
                    "name": {"title": "Name", "description": "The name", "type": "string"},
                    "tournament": {
                        "title": "Tournament",
                        "description": "What tournaments is a happenin'",
                        "allOf": [{"$ref": "#/definitions/tests.testmodels.Tournament.leaf"}],
                    },
                    "reporter": {
                        "title": "Reporter",
                        "nullable": True,
                        "allOf": [{"$ref": "#/definitions/tests.testmodels.Reporter.leaf"}],
                    },
                    "participants": {
                        "title": "Participants",
                        "type": "array",
                        "items": {"$ref": "#/definitions/tests.testmodels.Team.leaf"},
                    },
                    "modified": {
                        "title": "Modified",
                        "readOnly": True,
                        "type": "string",
                        "format": "date-time",
                    },
                    "token": {"title": "Token", "type": "string"},
                    "alias": {
                        "title": "Alias",
                        "minimum": -2147483648,
                        "maximum": 2147483647,
                        "nullable": True,
                        "type": "integer",
                    },
                    "address": {
                        "title": "Address",
                        "nullable": True,
                        "allOf": [{"$ref": "#/definitions/tests.testmodels.Address.leaf"}],
                    },
                },
                "required": ["event_id", "name", "tournament", "participants", "modified"],
                "additionalProperties": False,
                "definitions": {
                    "tests.testmodels.Tournament.leaf": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 32767,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "maxLength": 255, "type": "string"},
                            "desc": {"title": "Desc", "nullable": True, "type": "string"},
                            "created": {
                                "title": "Created",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                        "required": ["id", "name", "created"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Reporter.leaf": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Team.leaf": {
                        "title": "Team",
                        "description": "Team that is a playing",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Address.leaf": {
                        "title": "Address",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "city": {"title": "City", "maxLength": 64, "type": "string"},
                            "street": {"title": "Street", "maxLength": 128, "type": "string"},
                        },
                        "required": ["city", "street", "event_id"],
                        "additionalProperties": False,
                    },
                },
            },
        )

    def test_eventlist_schema(self):
        self.assertEqual(
            self.Event_Pydantic_List.schema(),
            {
                "title": "Event_list",
                "description": "Events on the calendar",
                "type": "array",
                "items": {"$ref": "#/definitions/tests.testmodels.Event"},
                "definitions": {
                    "tests.testmodels.Tournament.leaf": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 32767,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "maxLength": 255, "type": "string"},
                            "desc": {"title": "Desc", "nullable": True, "type": "string"},
                            "created": {
                                "title": "Created",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                        "required": ["id", "name", "created"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Reporter.leaf": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Team.leaf": {
                        "title": "Team",
                        "description": "Team that is a playing",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Address.leaf": {
                        "title": "Address",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "city": {"title": "City", "maxLength": 64, "type": "string"},
                            "street": {"title": "Street", "maxLength": 128, "type": "string"},
                        },
                        "required": ["city", "street", "event_id"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Event": {
                        "title": "Event",
                        "description": "Events on the calendar",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "description": "The name", "type": "string"},
                            "tournament": {
                                "title": "Tournament",
                                "description": "What tournaments is a happenin'",
                                "allOf": [
                                    {"$ref": "#/definitions/tests.testmodels.Tournament.leaf"}
                                ],
                            },
                            "reporter": {
                                "title": "Reporter",
                                "nullable": True,
                                "allOf": [{"$ref": "#/definitions/tests.testmodels.Reporter.leaf"}],
                            },
                            "participants": {
                                "title": "Participants",
                                "type": "array",
                                "items": {"$ref": "#/definitions/tests.testmodels.Team.leaf"},
                            },
                            "modified": {
                                "title": "Modified",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                            "token": {"title": "Token", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                            "address": {
                                "title": "Address",
                                "nullable": True,
                                "allOf": [{"$ref": "#/definitions/tests.testmodels.Address.leaf"}],
                            },
                        },
                        "required": ["event_id", "name", "tournament", "participants", "modified"],
                        "additionalProperties": False,
                    },
                },
            },
        )

    def test_address_schema(self):
        self.assertEqual(
            self.Address_Pydantic.schema(),
            {
                "title": "Address",
                "type": "object",
                "properties": {
                    "city": {"title": "City", "maxLength": 64, "type": "string"},
                    "street": {"title": "Street", "maxLength": 128, "type": "string"},
                    "event": {
                        "title": "Event",
                        "allOf": [{"$ref": "#/definitions/tests.testmodels.Event.orhjcw"}],
                    },
                    "event_id": {
                        "title": "Event Id",
                        "minimum": 1,
                        "maximum": 9223372036854775807,
                        "type": "integer",
                    },
                },
                "required": ["city", "street", "event", "event_id"],
                "additionalProperties": False,
                "definitions": {
                    "tests.testmodels.Tournament.leaf": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 32767,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "maxLength": 255, "type": "string"},
                            "desc": {"title": "Desc", "nullable": True, "type": "string"},
                            "created": {
                                "title": "Created",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                        "required": ["id", "name", "created"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Reporter.leaf": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Team.leaf": {
                        "title": "Team",
                        "description": "Team that is a playing",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Event.orhjcw": {
                        "title": "Event",
                        "description": "Events on the calendar",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "description": "The name", "type": "string"},
                            "tournament": {
                                "title": "Tournament",
                                "description": "What tournaments is a happenin'",
                                "allOf": [
                                    {"$ref": "#/definitions/tests.testmodels.Tournament.leaf"}
                                ],
                            },
                            "reporter": {
                                "title": "Reporter",
                                "nullable": True,
                                "allOf": [{"$ref": "#/definitions/tests.testmodels.Reporter.leaf"}],
                            },
                            "participants": {
                                "title": "Participants",
                                "type": "array",
                                "items": {"$ref": "#/definitions/tests.testmodels.Team.leaf"},
                            },
                            "modified": {
                                "title": "Modified",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                            "token": {"title": "Token", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                        },
                        "required": ["event_id", "name", "tournament", "participants", "modified"],
                        "additionalProperties": False,
                    },
                },
            },
        )

    def test_tournament_schema(self):
        self.assertEqual(
            self.Tournament_Pydantic.schema(),
            {
                "title": "Tournament",
                "type": "object",
                "properties": {
                    "id": {"title": "Id", "minimum": 1, "maximum": 32767, "type": "integer"},
                    "name": {"title": "Name", "maxLength": 255, "type": "string"},
                    "desc": {"title": "Desc", "nullable": True, "type": "string"},
                    "created": {
                        "title": "Created",
                        "readOnly": True,
                        "type": "string",
                        "format": "date-time",
                    },
                    "events": {
                        "title": "Events",
                        "description": "What tournaments is a happenin'",
                        "type": "array",
                        "items": {"$ref": "#/definitions/tests.testmodels.Event.b4oydv"},
                    },
                },
                "required": ["id", "name", "created", "events"],
                "additionalProperties": False,
                "definitions": {
                    "tests.testmodels.Reporter.leaf": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Team.leaf": {
                        "title": "Team",
                        "description": "Team that is a playing",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Address.leaf": {
                        "title": "Address",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "city": {"title": "City", "maxLength": 64, "type": "string"},
                            "street": {"title": "Street", "maxLength": 128, "type": "string"},
                        },
                        "required": ["city", "street", "event_id"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Event.b4oydv": {
                        "title": "Event",
                        "description": "Events on the calendar",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "description": "The name", "type": "string"},
                            "reporter": {
                                "title": "Reporter",
                                "nullable": True,
                                "allOf": [{"$ref": "#/definitions/tests.testmodels.Reporter.leaf"}],
                            },
                            "participants": {
                                "title": "Participants",
                                "type": "array",
                                "items": {"$ref": "#/definitions/tests.testmodels.Team.leaf"},
                            },
                            "modified": {
                                "title": "Modified",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                            "token": {"title": "Token", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                            "address": {
                                "title": "Address",
                                "nullable": True,
                                "allOf": [{"$ref": "#/definitions/tests.testmodels.Address.leaf"}],
                            },
                        },
                        "required": ["event_id", "name", "participants", "modified"],
                        "additionalProperties": False,
                    },
                },
            },
        )

    def test_team_schema(self):
        self.assertEqual(
            self.Team_Pydantic.schema(),
            {
                "title": "Team",
                "description": "Team that is a playing",
                "type": "object",
                "properties": {
                    "id": {"title": "Id", "minimum": 1, "maximum": 2147483647, "type": "integer"},
                    "name": {"title": "Name", "type": "string"},
                    "alias": {
                        "title": "Alias",
                        "minimum": -2147483648,
                        "maximum": 2147483647,
                        "nullable": True,
                        "type": "integer",
                    },
                    "events": {
                        "title": "Events",
                        "type": "array",
                        "items": {"$ref": "#/definitions/tests.testmodels.Event.dlqoeq"},
                    },
                },
                "required": ["id", "name", "events"],
                "additionalProperties": False,
                "definitions": {
                    "tests.testmodels.Tournament.leaf": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 32767,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "maxLength": 255, "type": "string"},
                            "desc": {"title": "Desc", "nullable": True, "type": "string"},
                            "created": {
                                "title": "Created",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                        "required": ["id", "name", "created"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Reporter.leaf": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "type": "string"},
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Address.leaf": {
                        "title": "Address",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "city": {"title": "City", "maxLength": 64, "type": "string"},
                            "street": {"title": "Street", "maxLength": 128, "type": "string"},
                        },
                        "required": ["city", "street", "event_id"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Event.dlqoeq": {
                        "title": "Event",
                        "description": "Events on the calendar",
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "title": "Event Id",
                                "minimum": 1,
                                "maximum": 9223372036854775807,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "description": "The name", "type": "string"},
                            "tournament": {
                                "title": "Tournament",
                                "description": "What tournaments is a happenin'",
                                "allOf": [
                                    {"$ref": "#/definitions/tests.testmodels.Tournament.leaf"}
                                ],
                            },
                            "reporter": {
                                "title": "Reporter",
                                "nullable": True,
                                "allOf": [{"$ref": "#/definitions/tests.testmodels.Reporter.leaf"}],
                            },
                            "modified": {
                                "title": "Modified",
                                "readOnly": True,
                                "type": "string",
                                "format": "date-time",
                            },
                            "token": {"title": "Token", "type": "string"},
                            "alias": {
                                "title": "Alias",
                                "minimum": -2147483648,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                            "address": {
                                "title": "Address",
                                "nullable": True,
                                "allOf": [{"$ref": "#/definitions/tests.testmodels.Address.leaf"}],
                            },
                        },
                        "required": ["event_id", "name", "tournament", "modified"],
                        "additionalProperties": False,
                    },
                },
            },
        )

    async def test_eventlist(self):
        eventlp = await self.Event_Pydantic_List.from_queryset(Event.all())
        # print(eventlp.json(indent=4))
        eventldict = eventlp.dict()["__root__"]

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
        eventdict = eventp.dict()

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
        addressdict = addressp.dict()

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
        tournamentdict = tournamentp.dict()

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
        teamdict = teamp.dict()

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
        schema = Event_Named.schema()
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
        schema = Event_Named.schema()
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
        schema = Event_Named.schema()
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
        ret0 = creator.from_orm(json_field_0_get).dict()
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
        ret1 = creator.from_orm(json_field_1_get).dict()
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

    def test_generated_pydantic_inherit_model_meta_config_class(self):
        """Generated class should inherit PydanticMeta's config_class"""
        ModelPydantic = pydantic_model_creator(CamelCaseAliasPerson, name="AutoAliasPerson")
        ExpectedParentConfig = CamelCaseAliasPerson.PydanticMeta.config_class

        self.assertTrue(issubclass(ModelPydantic.Config, ExpectedParentConfig))

    def test_override_default_model_config_by_config_class(self):
        """Pydantic meta's config_class should be able to override default config."""
        CamelCaseAliasPersonCopy = copy.deepcopy(CamelCaseAliasPerson)
        # Set class pydantic config's orm_mode to False
        CamelCaseAliasPersonCopy.PydanticMeta.config_class.orm_mode = False

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson, name="AutoAliasPersonOverriddenORMMode"
        )

        self.assertEqual(ModelPydantic.Config.orm_mode, False)

    def test_override_meta_pydantic_config_by_model_creator(self):
        """Tests config_class parameters' importance order.

        - pydantic_model_creator's config_class parameter should be able to override
            model PydanticMeta's config_class.
        """

        class AnotherConfigClass(PydanticBaseConfig):
            title = "Another title!"

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson,
            config_class=AnotherConfigClass,
            name="AutoAliasPersonModelCreatorConfig",
        )

        self.assertEqual(AnotherConfigClass.title, ModelPydantic.Config.title)

    def test_config_class_ignore_fields_config(self):
        """Generated config class should ignore config_class's fields parameter."""

        class FieldsConfig(PydanticBaseConfig):
            fields = ["id"]

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson, name="AutoAliasPersonCustomFields", config_class=FieldsConfig
        )

        self.assertNotEqual(ModelPydantic.Config.fields, FieldsConfig.fields)

    def test_config_classes_merge_all_configs(self):
        """Model creator should merge all 3 configs.

        - It merges (Default, Meta's config_class and creator's config_class) together.
        """

        class MinLengthConfig(PydanticBaseConfig):
            min_anystr_length = 3

        ModelPydantic = pydantic_model_creator(
            CamelCaseAliasPerson, name="AutoAliasPersonMinLength", config_class=MinLengthConfig
        )

        # Should set min_anystr_length from pydantic_model_creator's config_class
        self.assertEqual(ModelPydantic.Config.min_anystr_length, MinLengthConfig.min_anystr_length)
        # Should set title from model PydanticMeta's config_class
        self.assertEqual(
            ModelPydantic.Config.title, CamelCaseAliasPerson.PydanticMeta.config_class.title
        )
        # Should set orm_mode from base pydantic model configuration
        self.assertEqual(ModelPydantic.Config.orm_mode, PydanticModel.Config.orm_mode)


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
            self.Employee_Pydantic.schema(),
            {
                "title": "Employee",
                "type": "object",
                "properties": {
                    "id": {"title": "Id", "minimum": 1, "maximum": 2147483647, "type": "integer"},
                    "name": {"title": "Name", "maxLength": 50, "type": "string"},
                    "talks_to": {
                        "title": "Talks To",
                        "type": "array",
                        "items": {"$ref": "#/definitions/tests.testmodels.Employee.5gupxf"},
                    },
                    "manager_id": {
                        "title": "Manager Id",
                        "minimum": 1,
                        "maximum": 2147483647,
                        "nullable": True,
                        "type": "integer",
                    },
                    "team_members": {
                        "title": "Team Members",
                        "type": "array",
                        "items": {"$ref": "#/definitions/tests.testmodels.Employee.4fgkwn"},
                    },
                    "name_length": {"title": "Name Length", "type": "integer"},
                    "team_size": {
                        "title": "Team Size",
                        "description": "Computes team size.<br/><br/>Note that this function needs to be annotated with a return type so that pydantic can<br/> generate a valid schema.<br/><br/>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br/> pre-fetch relational data, so that it is available before serialization. So we don't<br/> need to await the relation. We do however have to protect against the case where no<br/> prefetching was done, hence catching and handling the<br/> ``tortoise.exceptions.NoValuesFetched`` exception.",
                        "type": "integer",
                    },
                },
                "required": ["id", "name", "talks_to", "team_members", "name_length", "team_size"],
                "additionalProperties": False,
                "definitions": {
                    "tests.testmodels.Employee.leaf": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "maxLength": 50, "type": "string"},
                            "manager_id": {
                                "title": "Manager Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br/><br/>Note that this function needs to be annotated with a return type so that pydantic can<br/> generate a valid schema.<br/><br/>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br/> pre-fetch relational data, so that it is available before serialization. So we don't<br/> need to await the relation. We do however have to protect against the case where no<br/> prefetching was done, hence catching and handling the<br/> ``tortoise.exceptions.NoValuesFetched`` exception.",
                                "type": "integer",
                            },
                        },
                        "required": ["id", "name", "name_length", "team_size"],
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Employee.5gupxf": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "maxLength": 50, "type": "string"},
                            "talks_to": {
                                "title": "Talks To",
                                "type": "array",
                                "items": {"$ref": "#/definitions/tests.testmodels.Employee.leaf"},
                            },
                            "manager_id": {
                                "title": "Manager Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                            "team_members": {
                                "title": "Team Members",
                                "type": "array",
                                "items": {"$ref": "#/definitions/tests.testmodels.Employee.leaf"},
                            },
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br/><br/>Note that this function needs to be annotated with a return type so that pydantic can<br/> generate a valid schema.<br/><br/>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br/> pre-fetch relational data, so that it is available before serialization. So we don't<br/> need to await the relation. We do however have to protect against the case where no<br/> prefetching was done, hence catching and handling the<br/> ``tortoise.exceptions.NoValuesFetched`` exception.",
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
                        "additionalProperties": False,
                    },
                    "tests.testmodels.Employee.4fgkwn": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "type": "integer",
                            },
                            "name": {"title": "Name", "maxLength": 50, "type": "string"},
                            "talks_to": {
                                "title": "Talks To",
                                "type": "array",
                                "items": {"$ref": "#/definitions/tests.testmodels.Employee.leaf"},
                            },
                            "manager_id": {
                                "title": "Manager Id",
                                "minimum": 1,
                                "maximum": 2147483647,
                                "nullable": True,
                                "type": "integer",
                            },
                            "team_members": {
                                "title": "Team Members",
                                "type": "array",
                                "items": {"$ref": "#/definitions/tests.testmodels.Employee.leaf"},
                            },
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br/><br/>Note that this function needs to be annotated with a return type so that pydantic can<br/> generate a valid schema.<br/><br/>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br/> pre-fetch relational data, so that it is available before serialization. So we don't<br/> need to await the relation. We do however have to protect against the case where no<br/> prefetching was done, hence catching and handling the<br/> ``tortoise.exceptions.NoValuesFetched`` exception.",
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
                        "additionalProperties": False,
                    },
                },
            },
        )

    async def test_serialisation(self):
        empp = await self.Employee_Pydantic.from_tortoise_orm(await Employee.get(name="Root"))
        # print(empp.json(indent=4))
        empdict = empp.dict()

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
            self.UserCreate_Pydantic.schema(),
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
            self.UserUpdate_Pydantic.schema(),
            {
                "title": "UserUpdate",
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
                "additionalProperties": False,
            },
        )
