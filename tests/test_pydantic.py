from tests.testmodels import Address, Event, Reporter, Team, Tournament
from tortoise.contrib import test
from tortoise.pydantic import pydantic_model_creator


class TestPydantic(test.TestCase):
    async def test_event(self):
        Event_Pydantic = pydantic_model_creator(Event)
        # print(Event_Pydantic.schema_json(indent=4))

        tournament = await Tournament.create(name="New Tournament")
        reporter = await Reporter.create(name="The Reporter")
        event = await Event.create(name="Test", tournament=tournament, reporter=reporter)
        address = await Address.create(city="Santa Monica", street="Ocean", event=event)
        team1 = await Team.create(name="Onesies")
        team2 = await Team.create(name="T-Shirts")
        await event.participants.add(team1, team2)

        eventp = await Event_Pydantic.from_tortoise_orm(await Event.all().first())
        # print(eventp.json(indent=4))
        eventdict = eventp.dict()

        # Massage to be repeatable
        del eventdict["modified"]
        del eventdict["tournament"]["created"]
        eventdict["participants"] = sorted(eventdict["participants"], key=lambda x: x["id"])

        self.assertEqual(
            eventdict,
            {
                "id": event.id,
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
                "address": {"id": address.pk, "city": "Santa Monica", "street": "Ocean"},
            },
        )
