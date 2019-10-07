"""
Tortoise PyLint plugin
"""
from typing import Dict, Iterator, List

from astroid import MANAGER, inference_tip, nodes, scoped_nodes
from astroid.node_classes import Assign
from astroid.nodes import ClassDef
from pylint.lint import PyLinter

MODELS: Dict[str, ClassDef] = {}
FUTURE_RELATIONS: Dict[str, list] = {}


def register(linter: PyLinter) -> None:
    """
    Reset state every time this is called, since we now get new AST to transform.
    """
    MODELS.clear()
    FUTURE_RELATIONS.clear()


def is_model(cls: ClassDef) -> bool:
    """
    Guard to apply this transform to Models only
    """
    return cls.metaclass() and cls.metaclass().qname() == "tortoise.models.ModelMeta"


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
                    if isinstance(attr, Assign):
                        if attr.targets[0].name == "app":
                            appname = attr.value.value

        mname = f"{appname}.{cls.name}"
        MODELS[mname] = cls

        for relname, relval in FUTURE_RELATIONS.get(mname, []):
            cls.locals[relname] = relval

        for attr in cls.get_children():
            if isinstance(attr, Assign):
                try:
                    attrname = attr.value.func.attrname
                except AttributeError:
                    pass
                else:
                    if attrname in ["ForeignKeyField", "ManyToManyField"]:
                        tomodel = attr.value.args[0].value
                        relname = ""
                        if attr.value.keywords:
                            for keyword in attr.value.keywords:
                                if keyword.arg == "related_name":
                                    relname = keyword.value.value

                        if not relname:
                            relname = cls.name.lower() + "s"

                        # Injected model attributes need to also have the relation manager
                        if attrname == "ManyToManyField":
                            relval = [
                                attr.value.func,
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "ManyToManyRelationManager"
                                )[1][0],
                            ]
                        else:
                            relval = [
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "BackwardFKRelation"
                                )[1][0],
                                MANAGER.ast_from_module_name("tortoise.fields.relational").lookup(
                                    "RelationQueryContainer"
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
        cls.locals["id"] = [nodes.ClassDef("id", None)]


def is_model_field(cls: ClassDef) -> bool:
    """
    Guard to apply this transform to Model Fields only
    """
    type_name = "tortoise.fields.base.Field"
    return cls.is_subtype_of(type_name) and cls.qname() != type_name


def apply_type_shim(cls: ClassDef, _context=None) -> Iterator[ClassDef]:
    """
    Morphs model fields to representative type
    """
    base_nodes: List[ClassDef] = []

    # Use the type inference standard
    ancestors = list(cls.ancestors())[2:]
    if ancestors:
        base_nodes = ancestors

    # Special types that can't use inference
    if cls.name == "BooleanField":
        base_nodes = scoped_nodes.builtin_lookup("bool")[1]

    return iter([cls] + base_nodes)


MANAGER.register_transform(nodes.ClassDef, inference_tip(apply_type_shim), is_model_field)
MANAGER.register_transform(nodes.ClassDef, transform_model, is_model)
