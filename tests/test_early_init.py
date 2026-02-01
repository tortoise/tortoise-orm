from tortoise import Tortoise, fields
from tortoise.contrib import test
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(primary_key=True)
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

    id = fields.IntField(primary_key=True)
    #: The Event NAME
    #:  It's pretty important
    name = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    tournament: fields.ForeignKeyNullableRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", null=True
    )

    class Meta:
        ordering = ["name"]


class TestBasic(test.SimpleTestCase):
    async def test_early_init(self):
        self.maxDiff = None
        Event_TooEarly = pydantic_model_creator(Event)
        self.assertEqual(
            Event_TooEarly.model_json_schema(),
            {
                "title": "Event",
                "type": "object",
                "description": "The Event model docstring.<br/><br/>This is multiline docs.",
                "properties": {
                    "id": {
                        "title": "Id",
                        "type": "integer",
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                    },
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
                "indexes": [],
                "pk_field": {
                    "name": "id",
                    "field_type": "IntField",
                    "db_column": "id",
                    "python_type": "int",
                    "generated": True,
                    "nullable": False,
                    "unique": True,
                    "indexed": True,
                    "default": None,
                    "description": None,
                    "docstring": None,
                    "constraints": {"ge": -2147483648, "le": 2147483647},
                    "db_field_types": {"": "INT"},
                },
                "data_fields": [
                    {
                        "name": "name",
                        "field_type": "CharField",
                        "db_column": "name",
                        "python_type": "str",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": "The Event NAME",
                        "docstring": "The Event NAME\nIt's pretty important",
                        "constraints": {"max_length": 255},
                        "db_field_types": {
                            "": "VARCHAR(255)",
                            "oracle": "NVARCHAR2(255)",
                        },
                    },
                    {
                        "name": "created_at",
                        "field_type": "DatetimeField",
                        "db_column": "created_at",
                        "python_type": "datetime.datetime",
                        "generated": False,
                        "nullable": False,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {"readOnly": True},
                        "db_field_types": {
                            "": "TIMESTAMP",
                            "mssql": "DATETIME2",
                            "mysql": "DATETIME(6)",
                            "postgres": "TIMESTAMPTZ",
                            "oracle": "TIMESTAMP WITH TIME ZONE",
                        },
                        "auto_now_add": True,
                        "auto_now": False,
                    },
                ],
                "fk_fields": [
                    {
                        "name": "tournament",
                        "field_type": "ForeignKeyFieldInstance",
                        "python_type": "None",
                        "generated": False,
                        "nullable": True,
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {},
                        "raw_field": None,
                        "on_delete": "CASCADE",
                        "db_constraint": True,
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
            Event_Pydantic.model_json_schema(),
            {
                "$defs": {
                    "Tournament_aapnxb_leaf": {
                        "additionalProperties": False,
                        "properties": {
                            "id": {
                                "maximum": 2147483647,
                                "minimum": -2147483648,
                                "title": "Id",
                                "type": "integer",
                            },
                            "name": {"maxLength": 100, "title": "Name", "type": "string"},
                            "created_at": {
                                "format": "date-time",
                                "readOnly": True,
                                "title": "Created At",
                                "type": "string",
                            },
                        },
                        "required": ["id", "name", "created_at"],
                        "title": "Tournament",
                        "type": "object",
                    }
                },
                "additionalProperties": False,
                "description": "The Event model docstring.<br/><br/>This is multiline docs.",
                "properties": {
                    "id": {
                        "maximum": 2147483647,
                        "minimum": -2147483648,
                        "title": "Id",
                        "type": "integer",
                    },
                    "name": {
                        "description": "The Event NAME<br/>It's pretty important",
                        "maxLength": 255,
                        "title": "Name",
                        "type": "string",
                    },
                    "created_at": {
                        "format": "date-time",
                        "readOnly": True,
                        "title": "Created At",
                        "type": "string",
                    },
                    "tournament": {
                        "anyOf": [{"$ref": "#/$defs/Tournament_aapnxb_leaf"}, {"type": "null"}],
                        "nullable": True,
                        "title": "Tournament",
                    },
                },
                "required": ["id", "name", "created_at", "tournament"],
                "title": "Event",
                "type": "object",
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
                "indexes": [],
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
                    "constraints": {"ge": -2147483648, "le": 2147483647},
                },
                "data_fields": [
                    {
                        "name": "name",
                        "field_type": "CharField",
                        "db_column": "name",
                        "db_field_types": {
                            "": "VARCHAR(255)",
                            "oracle": "NVARCHAR2(255)",
                        },
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
                            "mssql": "DATETIME2",
                            "mysql": "DATETIME(6)",
                            "postgres": "TIMESTAMPTZ",
                            "oracle": "TIMESTAMP WITH TIME ZONE",
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
                        "auto_now_add": True,
                        "auto_now": False,
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
                        "constraints": {"ge": -2147483648, "le": 2147483647},
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
                        "on_delete": "CASCADE",
                        "unique": False,
                        "indexed": False,
                        "default": None,
                        "description": None,
                        "docstring": None,
                        "constraints": {},
                        "db_constraint": True,
                    }
                ],
                "backward_fk_fields": [],
                "o2o_fields": [],
                "backward_o2o_fields": [],
                "m2m_fields": [],
            },
        )
