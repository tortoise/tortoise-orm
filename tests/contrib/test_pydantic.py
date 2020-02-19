from tests.testmodels import Address, Employee, Event, Reporter, Team, Tournament
from tortoise.contrib import test
from tortoise.contrib.pydantic import pydantic_model_creator, pydantic_queryset_creator


class TestPydantic(test.TestCase):
    async def setUp(self) -> None:
        self.Event_Pydantic = pydantic_model_creator(Event)
        self.Event_Pydantic_List = pydantic_queryset_creator(Event)
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
                    "event_id": {"title": "Event Id", "type": "integer"},
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

    def test_eventlist_schema(self):
        self.assertEqual(
            self.Event_Pydantic_List.schema(),
            {
                "title": "Events",
                "description": "Events on the calendar",
                "type": "array",
                "items": {"$ref": "#/definitions/Event"},
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
                    "Event": {
                        "title": "Event",
                        "description": "Events on the calendar",
                        "type": "object",
                        "properties": {
                            "event_id": {"title": "Event Id", "type": "integer"},
                            "name": {"title": "Name", "description": "The name", "type": "string"},
                            "modified": {
                                "title": "Modified",
                                "type": "string",
                                "format": "date-time",
                            },
                            "token": {"title": "Token", "type": "string"},
                            "alias": {"title": "Alias", "type": "integer"},
                            "tournament": {
                                "title": "Tournament",
                                "description": "What tournaments is a happenin'",
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
                            "address": {
                                "title": "Address",
                                "allOf": [{"$ref": "#/definitions/Address"}],
                            },
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
                            "event_id": {"title": "Event Id", "type": "integer"},
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
                            "event_id": {"title": "Event Id", "type": "integer"},
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
                    "address": {"id": self.address.pk, "city": "Santa Monica", "street": "Ocean"},
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
                            "id": self.address.pk,
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
                            "id": self.address.pk,
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


class TestPydanticCycle(test.TestCase):
    async def setUp(self) -> None:
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
                    "id": {"title": "Id", "type": "integer"},
                    "name": {"title": "Name", "type": "string"},
                    "manager_id": {"title": "Manager Id", "type": "integer"},
                    "talks_to": {
                        "title": "Talks To",
                        "type": "array",
                        "items": {"$ref": "#/definitions/Employee_0d9ca741"},
                    },
                    "team_members": {
                        "title": "Team Members",
                        "type": "array",
                        "items": {"$ref": "#/definitions/Employee_f5fb07fd"},
                    },
                    "name_length": {"title": "Name Length", "type": "integer"},
                    "team_size": {
                        "title": "Team Size",
                        "description": "Computes team size.<br><br>Note that this function needs to be annotated with a return type so that pydantic can<br> generate a valid schema.<br><br>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br> pre-fetch relational data, so that it is available before serialization. So we don't<br> need to await the relation. We do however have to protect against the case where no<br> prefetching was done, hence catching and handling the<br> ``tortoise.exceptions.NoValuesFetched`` exception.",
                        "type": "integer",
                    },
                },
                "definitions": {
                    "Employee_f9f05e47": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "manager_id": {"title": "Manager Id", "type": "integer"},
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br><br>Note that this function needs to be annotated with a return type so that pydantic can<br> generate a valid schema.<br><br>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br> pre-fetch relational data, so that it is available before serialization. So we don't<br> need to await the relation. We do however have to protect against the case where no<br> prefetching was done, hence catching and handling the<br> ``tortoise.exceptions.NoValuesFetched`` exception.",
                                "type": "integer",
                            },
                        },
                    },
                    "Employee_992cd278": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "manager_id": {"title": "Manager Id", "type": "integer"},
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br><br>Note that this function needs to be annotated with a return type so that pydantic can<br> generate a valid schema.<br><br>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br> pre-fetch relational data, so that it is available before serialization. So we don't<br> need to await the relation. We do however have to protect against the case where no<br> prefetching was done, hence catching and handling the<br> ``tortoise.exceptions.NoValuesFetched`` exception.",
                                "type": "integer",
                            },
                        },
                    },
                    "Employee_0d9ca741": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "manager_id": {"title": "Manager Id", "type": "integer"},
                            "talks_to": {
                                "title": "Talks To",
                                "type": "array",
                                "items": {"$ref": "#/definitions/Employee_f9f05e47"},
                            },
                            "team_members": {
                                "title": "Team Members",
                                "type": "array",
                                "items": {"$ref": "#/definitions/Employee_992cd278"},
                            },
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br><br>Note that this function needs to be annotated with a return type so that pydantic can<br> generate a valid schema.<br><br>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br> pre-fetch relational data, so that it is available before serialization. So we don't<br> need to await the relation. We do however have to protect against the case where no<br> prefetching was done, hence catching and handling the<br> ``tortoise.exceptions.NoValuesFetched`` exception.",
                                "type": "integer",
                            },
                        },
                    },
                    "Employee_297c851f": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "manager_id": {"title": "Manager Id", "type": "integer"},
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br><br>Note that this function needs to be annotated with a return type so that pydantic can<br> generate a valid schema.<br><br>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br> pre-fetch relational data, so that it is available before serialization. So we don't<br> need to await the relation. We do however have to protect against the case where no<br> prefetching was done, hence catching and handling the<br> ``tortoise.exceptions.NoValuesFetched`` exception.",
                                "type": "integer",
                            },
                        },
                    },
                    "Employee_db6253ef": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "manager_id": {"title": "Manager Id", "type": "integer"},
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br><br>Note that this function needs to be annotated with a return type so that pydantic can<br> generate a valid schema.<br><br>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br> pre-fetch relational data, so that it is available before serialization. So we don't<br> need to await the relation. We do however have to protect against the case where no<br> prefetching was done, hence catching and handling the<br> ``tortoise.exceptions.NoValuesFetched`` exception.",
                                "type": "integer",
                            },
                        },
                    },
                    "Employee_f5fb07fd": {
                        "title": "Employee",
                        "type": "object",
                        "properties": {
                            "id": {"title": "Id", "type": "integer"},
                            "name": {"title": "Name", "type": "string"},
                            "manager_id": {"title": "Manager Id", "type": "integer"},
                            "talks_to": {
                                "title": "Talks To",
                                "type": "array",
                                "items": {"$ref": "#/definitions/Employee_297c851f"},
                            },
                            "team_members": {
                                "title": "Team Members",
                                "type": "array",
                                "items": {"$ref": "#/definitions/Employee_db6253ef"},
                            },
                            "name_length": {"title": "Name Length", "type": "integer"},
                            "team_size": {
                                "title": "Team Size",
                                "description": "Computes team size.<br><br>Note that this function needs to be annotated with a return type so that pydantic can<br> generate a valid schema.<br><br>Note that the pydantic serializer can't call async methods, but the tortoise helpers<br> pre-fetch relational data, so that it is available before serialization. So we don't<br> need to await the relation. We do however have to protect against the case where no<br> prefetching was done, hence catching and handling the<br> ``tortoise.exceptions.NoValuesFetched`` exception.",
                                "type": "integer",
                            },
                        },
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
