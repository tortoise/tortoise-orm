"""
Tortoise PyLint plugin
"""
from typing import Iterator

from astroid import MANAGER, inference_tip, nodes, scoped_nodes
from astroid.node_classes import Assign
from astroid.nodes import ClassDef

MODELS = {}  # type: dict
FUTURE_RELATIONS = {}  # type: dict


def register(linter) -> None:
    """
    Reset state every time this is called, since we now get new AST to transform.
    """
    # pylint: disable=W0603
    global MODELS
    global FUTURE_RELATIONS
    MODELS = {}
    FUTURE_RELATIONS = {}


def is_model(cls) -> bool:
    """
    Guard to apply this transform to Models only
    """
    return cls.metaclass() and cls.metaclass().qname() == "tortoise.models.ModelMeta"


def transform_model(cls) -> None:
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

        mname = "{}.{}".format(appname, cls.name)
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
                                MANAGER.ast_from_module_name("tortoise.fields").lookup(
                                    "ManyToManyRelationManager"
                                )[1][0],
                            ]
                        else:
                            relval = [
                                attr.value.func,
                                MANAGER.ast_from_module_name("tortoise.fields").lookup(
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


def is_model_field(cls) -> bool:
    """
    Guard to apply this transform to Model Fields only
    """
    return cls.qname().startswith("tortoise.fields")


def apply_type_shim(cls, _context=None) -> Iterator:
    """
    Morphs model fields to representative type
    """
    if cls.name in ["IntField", "SmallIntField"]:
        base_nodes = scoped_nodes.builtin_lookup("int")
    elif cls.name in ["CharField", "TextField"]:
        base_nodes = scoped_nodes.builtin_lookup("str")
    elif cls.name == "BooleanField":
        base_nodes = scoped_nodes.builtin_lookup("bool")
    elif cls.name == "FloatField":
        base_nodes = scoped_nodes.builtin_lookup("float")
    elif cls.name == "DecimalField":
        base_nodes = MANAGER.ast_from_module_name("decimal").lookup("Decimal")
    elif cls.name == "DatetimeField":
        base_nodes = MANAGER.ast_from_module_name("datetime").lookup("datetime")
    elif cls.name == "DateField":
        base_nodes = MANAGER.ast_from_module_name("datetime").lookup("date")
    elif cls.name == "ForeignKeyField":
        base_nodes = MANAGER.ast_from_module_name("tortoise.fields").lookup("BackwardFKRelation")
    elif cls.name == "ManyToManyField":
        base_nodes = MANAGER.ast_from_module_name("tortoise.fields").lookup(
            "ManyToManyRelationManager"
        )
    else:
        return iter([cls])

    return iter([cls] + base_nodes[1])


MANAGER.register_transform(nodes.ClassDef, inference_tip(apply_type_shim), is_model_field)
MANAGER.register_transform(nodes.ClassDef, transform_model, is_model)
