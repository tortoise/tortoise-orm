import json

from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.tests.testmodels import (
    Event,
    JSONFields,
    Reporter,
    SourceFields,
    StraightFields,
    Team,
    Tournament,
    UUIDPkModel,
)


class TestBasic(test.TestCase):
    maxDiff = None

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

    async def test_describe_model_straight(self):
        val = Tortoise.describe_model(StraightFields)

        self.assertEqual(
            val,
            {
                "name": "models.StraightFields",
                "app": "models",
                "table": "straightfields",
                "abstract": False,
                "description": "Straight auto-mapped fields",
                "unique_together": [["chars", "blip"]],
                "pk_field": {
                    "name": "id",
                    "field_type": "IntField",
                    "db_column": "id",
                    "python_type": "int",
                    "generated": True,
                    "nullable": False,
                    "unique": False,
                    "indexed": False,
                    "default": None,
                    "description": "Da PK",
                },
                "data_fields": [
                    {
                        "name": "chars",
                        "field_type": "CharField",
                        "db_column": "chars",
                        "python_type": "str",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": True,
                        "default": None,
                        "description": "Some chars",
                    },
                    {
                        "name": "blip",
                        "field_type": "CharField",
                        "db_column": "blip",
                        "python_type": "str",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": "BLIP",
                        "description": None,
                    },
                    {
                        "name": "fk_id",
                        "field_type": "IntField",
                        "db_column": "fk_id",
                        "python_type": "int",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "Tree!",
                    },
                ],
                "fk_fields": [
                    {
                        "name": "fk",
                        "field_type": "ForeignKeyField",
                        "raw_field": "fk_id",
                        "python_type": "models.StraightFields",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "Tree!",
                    }
                ],
                "backward_fk_fields": [
                    {
                        "name": "fkrev",
                        "field_type": "BackwardFKRelation",
                        "python_type": "models.StraightFields",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "Tree!",
                    }
                ],
                "m2m_fields": [
                    {
                        "name": "rel_to",
                        "field_type": "ManyToManyField",
                        "python_type": "models.StraightFields",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "M2M to myself",
                    },
                    {
                        "name": "rel_from",
                        "field_type": "ManyToManyField",
                        "python_type": "models.StraightFields",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "M2M to myself",
                    },
                ],
            },
        )

    async def test_describe_model_source(self):
        val = Tortoise.describe_model(SourceFields)

        self.assertEqual(
            val,
            {
                "name": "models.SourceFields",
                "app": "models",
                "table": "sometable",
                "abstract": False,
                "description": "Source mapped fields",
                "unique_together": [["chars", "blip"]],
                "pk_field": {
                    "name": "id",
                    "field_type": "IntField",
                    "db_column": "sometable_id",
                    "python_type": "int",
                    "generated": True,
                    "nullable": False,
                    "unique": False,
                    "indexed": False,
                    "default": None,
                    "description": "Da PK",
                },
                "data_fields": [
                    {
                        "name": "chars",
                        "field_type": "CharField",
                        "db_column": "some_chars_table",
                        "python_type": "str",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": True,
                        "default": None,
                        "description": "Some chars",
                    },
                    {
                        "name": "blip",
                        "field_type": "CharField",
                        "db_column": "da_blip",
                        "python_type": "str",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": "BLIP",
                        "description": None,
                    },
                    {
                        "name": "fk_id",
                        "field_type": "IntField",
                        "db_column": "fk_sometable",
                        "python_type": "int",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "Tree!",
                    },
                ],
                "fk_fields": [
                    {
                        "name": "fk",
                        "field_type": "ForeignKeyField",
                        "raw_field": "fk_id",
                        "python_type": "models.SourceFields",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "Tree!",
                    }
                ],
                "backward_fk_fields": [
                    {
                        "name": "fkrev",
                        "field_type": "BackwardFKRelation",
                        "python_type": "models.SourceFields",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "Tree!",
                    }
                ],
                "m2m_fields": [
                    {
                        "name": "rel_to",
                        "field_type": "ManyToManyField",
                        "python_type": "models.SourceFields",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "M2M to myself",
                    },
                    {
                        "name": "rel_from",
                        "field_type": "ManyToManyField",
                        "python_type": "models.SourceFields",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "M2M to myself",
                    },
                ],
            },
        )

    async def test_describe_model_uuidpk(self):
        val = Tortoise.describe_model(UUIDPkModel)

        self.assertEqual(
            val,
            {
                "name": "models.UUIDPkModel",
                "app": "models",
                "table": "uuidpkmodel",
                "abstract": False,
                "description": None,
                "unique_together": [],
                "pk_field": {
                    "name": "id",
                    "field_type": "UUIDField",
                    "db_column": "id",
                    "python_type": "uuid.UUID",
                    "generated": False,
                    "nullable": False,
                    "unique": False,
                    "indexed": False,
                    "default": "<function uuid.uuid4>",
                    "description": None,
                },
                "data_fields": [],
                "fk_fields": [],
                "backward_fk_fields": [
                    {
                        "name": "children",
                        "field_type": "BackwardFKRelation",
                        "python_type": "models.UUIDFkRelatedModel",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                    }
                ],
                "m2m_fields": [
                    {
                        "name": "peers",
                        "field_type": "ManyToManyField",
                        "python_type": "models.UUIDM2MRelatedModel",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                    }
                ],
            },
        )

    async def test_describe_model_json(self):
        val = Tortoise.describe_model(JSONFields)

        self.assertEqual(
            val,
            {
                "name": "models.JSONFields",
                "app": "models",
                "table": "jsonfields",
                "abstract": False,
                "description": None,
                "unique_together": [],
                "pk_field": {
                    "name": "id",
                    "field_type": "IntField",
                    "db_column": "id",
                    "python_type": "int",
                    "generated": True,
                    "nullable": False,
                    "unique": False,
                    "indexed": False,
                    "default": None,
                    "description": None,
                },
                "data_fields": [
                    {
                        "name": "data",
                        "field_type": "JSONField",
                        "db_column": "data",
                        "python_type": ["dict", "list"],
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                    },
                    {
                        "name": "data_null",
                        "field_type": "JSONField",
                        "db_column": "data_null",
                        "python_type": ["dict", "list"],
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                    },
                ],
                "fk_fields": [],
                "backward_fk_fields": [],
                "m2m_fields": [],
            },
        )
