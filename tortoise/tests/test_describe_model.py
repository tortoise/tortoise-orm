import json

from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.tests.testmodels import Event, Reporter, Team, Tournament


class TestBasic(test.TestCase):
    async def test_describe_models_all_serializable(self):
        val = Tortoise.describe_models()
        json.dumps(val)
        self.assertIn("models.SourceFields", val.keys())
        self.assertIn("models.Event", val.keys())

    async def test_describe_models_all_not_serializable(self):
        val = Tortoise.describe_models(serializable=False)
        with self.assertRaisesRegex(TypeError, "not JSON serializable"):
            json.dumps(val)
        self.assertIn("models.SourceFields", val.keys())
        self.assertIn("models.Event", val.keys())

    async def test_describe_models_some(self):
        val = Tortoise.describe_models([Event, Tournament, Reporter, Team])
        self.assertEqual(
            {"models.Event", "models.Tournament", "models.Reporter", "models.Team"}, set(val.keys())
        )

    async def test_describe_model_event(self):
        val = Tortoise.describe_model(Event)
        print(val)
