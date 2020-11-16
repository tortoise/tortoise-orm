from tortoise import Tortoise, fields
from tortoise.contrib import test
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ReverseRelation["Event"]

    class Meta:
        ordering = ["name"]


class Event(Model):
    """
    The Event model docstring.

    This is multiline docs.
    """

    id = fields.IntField(pk=True)
    #: The Event NAME
    #:  It's pretty important
    name = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    tournament: fields.ForeignKeyNullableRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", null=True
    )

    class Meta:
        ordering = ["name"]


class TestBasic(test.TestCase):
    def test_early_init(self):

        self.maxDiff = None
        Event_TooEarly = pydantic_model_creator(Event)
        self.assertEqual(
            Event_TooEarly.schema(),
            {
                "title": "Event",
                "type": "object",
                "description": "The Event model docstring.<br/><br/>This is multiline docs.",
                "properties": {
                    "id": {"title": "Id", "type": "integer", "maximum": 2147483647, "minimum": 1},
                    "name": {
                        "title": "Name",
                        "type": "string",
                        "description": "The Event NAME<br/>It's pretty important",
                        "maxLength": 255,
                    },
                    "created_at": {
                        "title": "Created At",
                        "type": "string",
                        "format": "date-time",
                        "readOnly": True,
                    },
                },
                "required": ["id", "name", "created_at"],
                "additionalProperties": False,
            },
        )
        self.assertEqual(
            Event.describe(),
            {
                "name": "None.Event",
                "app": None,
                "table": "",
                "abstract": False,
                "description": "The Event model docstring.",
                "docstring": "The Event model docstring.\n\nThis is multiline docs.",
                "unique_together": [],
                "pk_field": {
                    "name": "id",
                    "field_type": "IntField",
                    "db_column": "id",
                    "db_field_types": {"": "INT"},
                    "python_type": "int",
                    "generated": True,
                    "nullable": False,
                    "unique": True,
                    "indexed": True,
                    "default": None,
                    "description": None,
                    "docstring": None,
                    "constraints": {"ge": 1, "le": 2147483647},
                },
                "data_fields": [
                    {
                        "name": "name",
                        "field_type": "CharField",
                        "db_column": "name",
                        "db_field_types": {"": "VARCHAR(255)"},
                        "python_type": "str",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "The Event NAME",
                        "docstring": "The Event NAME\nIt's pretty important",
                        "constraints": {"max_length": 255},
                    },
                    {
                        "name": "created_at",
                        "field_type": "DatetimeField",
                        "db_column": "created_at",
                        "db_field_types": {
                            "": "TIMESTAMP",
                            "mysql": "DATETIME(6)",
                            "postgres": "TIMESTAMPTZ",
                        },
                        "python_type": "datetime.datetime",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {"readOnly": True},
                    },
                ],
                "fk_fields": [
                    {
                        "name": "tournament",
                        "field_type": "ForeignKeyFieldInstance",
                        "raw_field": None,
                        "python_type": "None",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {},
                    }
                ],
                "backward_fk_fields": [],
                "o2o_fields": [],
                "backward_o2o_fields": [],
                "m2m_fields": [],
            },
        )

        Tortoise.init_models(["tests.test_early_init"], "models")

        Event_Pydantic = pydantic_model_creator(Event)
        self.assertEqual(
            Event_Pydantic.schema(),
            {
                "title": "Event",
                "type": "object",
                "description": "The Event model docstring.<br/><br/>This is multiline docs.",
                "properties": {
                    "id": {"title": "Id", "type": "integer", "maximum": 2147483647, "minimum": 1},
                    "name": {
                        "title": "Name",
                        "type": "string",
                        "description": "The Event NAME<br/>It's pretty important",
                        "maxLength": 255,
                    },
                    "created_at": {
                        "title": "Created At",
                        "type": "string",
                        "format": "date-time",
                        "readOnly": True,
                    },
                    "tournament": {
                        "title": "Tournament",
                        "nullable": True,
                        "allOf": [{"$ref": "#/definitions/tests.test_early_init.Tournament.leaf"}],
                    },
                },
                "definitions": {
                    "tests.test_early_init.Tournament.leaf": {
                        "title": "Tournament",
                        "type": "object",
                        "properties": {
                            "id": {
                                "title": "Id",
                                "type": "integer",
                                "maximum": 2147483647,
                                "minimum": 1,
                            },
                            "name": {"title": "Name", "type": "string", "maxLength": 100},
                            "created_at": {
                                "title": "Created At",
                                "type": "string",
                                "format": "date-time",
                                "readOnly": True,
                            },
                        },
                        "required": ["id", "name", "created_at"],
                        "additionalProperties": False,
                    }
                },
                "required": ["id", "name", "created_at"],
                "additionalProperties": False,
            },
        )
        self.assertEqual(
            Event.describe(),
            {
                "name": "models.Event",
                "app": "models",
                "table": "event",
                "abstract": False,
                "description": "The Event model docstring.",
                "docstring": "The Event model docstring.\n\nThis is multiline docs.",
                "unique_together": [],
                "pk_field": {
                    "name": "id",
                    "field_type": "IntField",
                    "db_column": "id",
                    "db_field_types": {"": "INT"},
                    "python_type": "int",
                    "generated": True,
                    "nullable": False,
                    "unique": True,
                    "indexed": True,
                    "default": None,
                    "description": None,
                    "docstring": None,
                    "constraints": {"ge": 1, "le": 2147483647},
                },
                "data_fields": [
                    {
                        "name": "name",
                        "field_type": "CharField",
                        "db_column": "name",
                        "db_field_types": {"": "VARCHAR(255)"},
                        "python_type": "str",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "The Event NAME",
                        "docstring": "The Event NAME\nIt's pretty important",
                        "constraints": {"max_length": 255},
                    },
                    {
                        "name": "created_at",
                        "field_type": "DatetimeField",
                        "db_column": "created_at",
                        "db_field_types": {
                            "": "TIMESTAMP",
                            "mysql": "DATETIME(6)",
                            "postgres": "TIMESTAMPTZ",
                        },
                        "python_type": "datetime.datetime",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {"readOnly": True},
                    },
                    {
                        "name": "tournament_id",
                        "field_type": "IntField",
                        "db_column": "tournament_id",
                        "db_field_types": {"": "INT"},
                        "python_type": "int",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {"ge": 1, "le": 2147483647},
                    },
                ],
                "fk_fields": [
                    {
                        "name": "tournament",
                        "field_type": "ForeignKeyFieldInstance",
                        "raw_field": "tournament_id",
                        "python_type": "models.Tournament",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {},
                    }
                ],
                "backward_fk_fields": [],
                "o2o_fields": [],
                "backward_o2o_fields": [],
                "m2m_fields": [],
            },
        )
