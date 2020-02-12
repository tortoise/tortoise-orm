from tests.testmodels import Address, Event, Reporter, Team, Tournament
from tortoise.contrib import test
from tortoise.pydantic import pydantic_model_creator


class TestPydantic(test.TestCase):
    async def setUp(self) -> None:
        self.Event_Pydantic = pydantic_model_creator(Event)
        self.Tournament_Pydantic = pydantic_model_creator(Tournament)
        self.Team_Pydantic = pydantic_model_creator(Team)

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

    def test_event_schema(self):
        self.assertEqual(
            self.Event_Pydantic.schema(),
            {
                "title": "Event",
                "description": "Events on the calendar",
                "type": "object",
                "properties": {
                    "id": {"title": "Id", "type": "integer"},
                    "name": {"description": "The name", "title": "Name", "type": "string"},
                    "modified": {"title": "Modified", "type": "string", "format": "date-time"},
                    "token": {"title": "Token", "type": "string"},
                    "alias": {"title": "Alias", "type": "integer"},
                    "tournament": {
                        "description": "What tournaments is a happenin'",
                        "title": "Tournament",
                        "allOf": [{"$ref": "#/definitions/Tournament"}],
                    },
                    "reporter": {
                        "title": "Reporter",
                        "allOf": [{"$ref": "#/definitions/Reporter"}],
                    },
                    "participants": {
                        "title": "Participants",
                        "type": "array",
                        "items": {"$ref": "#/definitions/Team"},
                    },
                    "address": {"title": "Address", "allOf": [{"$ref": "#/definitions/Address"}]},
                },
                "definitions": {
                    "Tournament": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "desc": {"title": "Desc", "type": "string"},
                            "created": {
                                "title": "Created",
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                    },
                    "Reporter": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                        },
                    },
                    "Team": {
                        "title": "Team",
                        "description": "Team that is a playing",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "alias": {"title": "Alias", "type": "integer"},
                        },
                    },
                    "Address": {
                        "title": "Address",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "city": {"title": "City", "type": "string"},
                            "street": {"title": "Street", "type": "string"},
                        },
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
                    "id": {"title": "Id", "type": "integer"},
                    "name": {"title": "Name", "type": "string"},
                    "desc": {"title": "Desc", "type": "string"},
                    "created": {"title": "Created", "type": "string", "format": "date-time"},
                    "events": {
                        "title": "Events",
                        "type": "array",
                        "items": {"$ref": "#/definitions/Event"},
                    },
                },
                "definitions": {
                    "Reporter": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                        },
                    },
                    "Team": {
                        "title": "Team",
                        "description": "Team that is a playing",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "alias": {"title": "Alias", "type": "integer"},
                        },
                    },
                    "Address": {
                        "title": "Address",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "city": {"title": "City", "type": "string"},
                            "street": {"title": "Street", "type": "string"},
                        },
                    },
                    "Event": {
                        "title": "Event",
                        "description": "Events on the calendar",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"description": "The name", "title": "Name", "type": "string"},
                            "modified": {
                                "title": "Modified",
                                "type": "string",
                                "format": "date-time",
                            },
                            "token": {"title": "Token", "type": "string"},
                            "alias": {"title": "Alias", "type": "integer"},
                            "reporter": {
                                "title": "Reporter",
                                "allOf": [{"$ref": "#/definitions/Reporter"}],
                            },
                            "participants": {
                                "title": "Participants",
                                "type": "array",
                                "items": {"$ref": "#/definitions/Team"},
                            },
                            "address": {
                                "title": "Address",
                                "allOf": [{"$ref": "#/definitions/Address"}],
                            },
                        },
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
                    "id": {"title": "Id", "type": "integer"},
                    "name": {"title": "Name", "type": "string"},
                    "alias": {"title": "Alias", "type": "integer"},
                    "events": {
                        "title": "Events",
                        "type": "array",
                        "items": {"$ref": "#/definitions/Event"},
                    },
                },
                "definitions": {
                    "Tournament": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "desc": {"title": "Desc", "type": "string"},
                            "created": {
                                "title": "Created",
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                    },
                    "Reporter": {
                        "title": "Reporter",
                        "description": "Whom is assigned as the reporter",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                        },
                    },
                    "Address": {
                        "title": "Address",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "city": {"title": "City", "type": "string"},
                            "street": {"title": "Street", "type": "string"},
                        },
                    },
                    "Event": {
                        "title": "Event",
                        "description": "Events on the calendar",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"description": "The name", "title": "Name", "type": "string"},
                            "modified": {
                                "title": "Modified",
                                "type": "string",
                                "format": "date-time",
                            },
                            "token": {"title": "Token", "type": "string"},
                            "alias": {"title": "Alias", "type": "integer"},
                            "tournament": {
                                "description": "What tournaments is a happenin'",
                                "title": "Tournament",
                                "allOf": [{"$ref": "#/definitions/Tournament"}],
                            },
                            "reporter": {
                                "title": "Reporter",
                                "allOf": [{"$ref": "#/definitions/Reporter"}],
                            },
                            "address": {
                                "title": "Address",
                                "allOf": [{"$ref": "#/definitions/Address"}],
                            },
                        },
                    },
                },
            },
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
                "id": self.event.id,
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
                "address": {"id": self.address.pk, "city": "Santa Monica", "street": "Ocean"},
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
                        "id": self.event.id,
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
                            "id": self.address.pk,
                            "city": "Santa Monica",
                            "street": "Ocean",
                        },
                    },
                    {
                        "id": self.event2.id,
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
                        "id": self.event.id,
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
                            "id": self.address.pk,
                            "city": "Santa Monica",
                            "street": "Ocean",
                        },
                    },
                    {
                        "id": self.event2.id,
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
