"""
Tortoise PyLint plugin
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from astroid import MANAGER, inference_tip, nodes
from astroid.exceptions import AstroidError
from astroid.nodes import AnnAssign, Assign, ClassDef

if TYPE_CHECKING:
    from pylint.lint import PyLinter

MODELS: dict[str, ClassDef] = {}
FUTURE_RELATIONS: dict[str, list] = {}


def register(linter: PyLinter) -> None:  # pylint: disable=unused-argument
    """
    Reset state every time this is called, since we now get new AST to transform.
    """
    MODELS.clear()
    FUTURE_RELATIONS.clear()


def is_model(cls: ClassDef) -> bool:
    """
    Guard to apply this transform to Models only
    """
    return bool(cls.metaclass()) and cls.metaclass().qname() == "tortoise.models.ModelMeta"


def transform_model(cls: ClassDef) -> None:
    """
    Anything that uses the ModelMeta needs _meta and id.
    Also keep track of relationships and make them in the related model class.
    """
    if cls.name != "Model":
        appname = "models"
        for mcls in cls.get_children():
            if isinstance(mcls, ClassDef):
                for attr in mcls.get_children():
                    if isinstance(attr, Assign) and attr.targets[0].name == "app":
                        appname = attr.value.value

        mname = f"{appname}.{cls.name}"
        MODELS[mname] = cls

        for relname, relval in FUTURE_RELATIONS.get(mname, []):
            cls.locals[relname] = relval

        for attr in cls.get_children():
            if isinstance(attr, (Assign, AnnAssign)):
                try:
                    attrname = attr.value.func.attrname
                except AttributeError:
                    pass
                else:
                    if attrname in ["OneToOneField", "ForeignKeyField", "ManyToManyField"]:
                        tomodel = attr.value.args[0].value if attr.value.args else ""
                        relname = ""
                        if attr.value.keywords:
                            for keyword in attr.value.keywords:
                                if keyword.arg == "related_name":
                                    relname = keyword.value.value
                                if keyword.arg == "model_name":
                                    tomodel = keyword.value.value

                        if not relname:
                            relname = cls.name.lower() + "s"

                        # Injected model attributes need to also have the relation manager
                        if attrname == "ManyToManyField":
                            relval = [
                                # attr.value.func,
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "ManyToManyFieldInstance"
                                )[1][0],
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "ManyToManyRelation"
                                )[1][0],
                            ]
                        elif attrname == "ForeignKeyField":
                            relval = [
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "ForeignKeyFieldInstance"
                                )[1][0],
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "ReverseRelation"
                                )[1][0],
                            ]
                        elif attrname == "OneToOneField":
                            relval = [
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "OneToOneFieldInstance"
                                )[1][0],
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "OneToOneRelation"
                                )[1][0],
                            ]

                        if tomodel in MODELS:
                            MODELS[tomodel].locals[relname] = relval
                        else:
                            FUTURE_RELATIONS.setdefault(tomodel, []).append((relname, relval))

    cls.locals["_meta"] = [
        MANAGER.ast_from_module_name("tortoise.models").lookup("MetaInfo")[1][0].instantiate_class()
    ]
    if "id" not in cls.locals:
        cls.locals["id"] = [
            nodes.ClassDef("id", None, None, None, end_lineno=None, end_col_offset=None)
        ]


def is_model_field(cls: ClassDef) -> bool:
    """
    Guard to apply this transform to Model Fields only
    """
    type_name = "tortoise.fields.base.Field"
    return bool(cls.is_subtype_of(type_name)) and cls.qname() != type_name


def apply_type_shim(cls: ClassDef, _context: Any = None) -> Iterator[ClassDef]:
    """
    Morphs model fields to representative type
    """
    base_nodes: list[ClassDef] = [cls]

    # Use the type inference standard
    try:
        base_nodes.extend(list(cls.getattr("field_type")[0].infer()))
    except AstroidError:
        pass

    return iter(base_nodes)


MANAGER.register_transform(nodes.ClassDef, inference_tip(apply_type_shim), is_model_field)
MANAGER.register_transform(nodes.ClassDef, transform_model, is_model)
