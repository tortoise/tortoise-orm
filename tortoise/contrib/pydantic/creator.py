import inspect
from base64 import b32encode
from hashlib import sha3_224
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

import pydantic

from tortoise import fields
from tortoise.contrib.pydantic.base import PydanticListModel, PydanticModel
from tortoise.contrib.pydantic.utils import get_annotations

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


_MODEL_INDEX: Dict[str, Type[PydanticModel]] = {}


class PydanticMeta:
    """
    The ``PydanticMeta`` class is used to configure metadata for generating the pydantic Model.

    Usage:

    .. code-block:: python3

        class Foo(Model):
            ...

            class PydanticMeta:
                exclude = ("foo", "baa")
                computed = ("count_peanuts", )
    """

    #: If not empty, only fields this property contains will be in the pydantic model
    include: Tuple[str, ...] = ()

    #: Fields listed in this property will be excluded from pydantic model
    exclude: Tuple[str, ...] = ()

    #: Computed fields can be listed here to use in pydantic model
    computed: Tuple[str, ...] = ()

    #: Use backward relations without annotations - not recommended, it can be huge data
    #: without control
    backward_relations: bool = True

    #: Maximum recursion level allowed
    max_recursion: int = 3

    #: Allow cycles in recursion - This can result in HUGE data - Be careful!
    #: Please use this with ``exclude``/``include`` and sane ``max_recursion``
    allow_cycles: bool = False

    #: If we should exclude raw fields (the ones have _id suffixes) of relations
    exclude_raw_fields: bool = True

    #: Sort fields alphabetically.
    #: If not set (or ``False``) then leave fields in declaration order
    sort_alphabetically: bool = False


def _br_it(val: str) -> str:
    return val.replace("\n", "<br/>").strip()


def _cleandoc(obj: Any) -> str:
    return _br_it(inspect.cleandoc(obj.__doc__ or ""))


def _pydantic_recursion_protector(
    cls: "Type[Model]",
    *,
    stack: tuple,
    exclude: Tuple[str, ...] = (),
    include: Tuple[str, ...] = (),
    computed: Tuple[str, ...] = (),
    name=None,
    allow_cycles: bool = False,
    sort_alphabetically: Optional[bool] = None,
) -> Optional[Type[PydanticModel]]:
    """
    It is an inner function to protect pydantic model creator against cyclic recursion
    """
    if not allow_cycles and cls in (c[0] for c in stack[:-1]):
        return None

    caller_fname = stack[0][1]
    prop_path = [caller_fname]  # It stores the fields in the hierarchy
    level = 1
    for _, parent_fname, parent_max_recursion in stack[1:]:
        # Check recursion level
        prop_path.insert(0, parent_fname)
        if level >= parent_max_recursion:
            # This is too verbose, Do we even need a way of reporting truncated models?
            # tortoise.logger.warning(
            #     "Recursion level %i has reached for model %s",
            #     level,
            #     parent_cls.__qualname__ + "." + ".".join(prop_path),
            # )
            return None

        level += 1

    return pydantic_model_creator(
        cls,
        exclude=exclude,
        include=include,
        computed=computed,
        name=name,
        _stack=stack,
        allow_cycles=allow_cycles,
        sort_alphabetically=sort_alphabetically,
    )


def pydantic_model_creator(
    cls: "Type[Model]",
    *,
    name=None,
    exclude: Tuple[str, ...] = (),
    include: Tuple[str, ...] = (),
    computed: Tuple[str, ...] = (),
    allow_cycles: Optional[bool] = None,
    sort_alphabetically: Optional[bool] = None,
    _stack: tuple = (),
    exclude_readonly: bool = False,
) -> Type[PydanticModel]:
    """
    Function to build `Pydantic Model <https://pydantic-docs.helpmanual.io/usage/models/>`__ off Tortoise Model.

    :param cls: The Tortoise Model
    :param name: Specify a custom name explicitly, instead of a generated name.
    :param exclude: Extra fields to exclude from the provided model.
    :param include: Extra fields to include from the provided model.
    :param computed: Extra computed fields to include from the provided model.
    :param allow_cycles: Do we allow any cycles in the generated model?
        This is only useful for recursive/self-referential models.

        A value of ``False`` (the default) will prevent any and all backtracking.
    :param sort_alphabetically: Sort the parameters alphabetically instead of Field-definition order.

        The default order would be:

            * Field definition order +
            * order of reverse relations (as discovered) +
            * order of computed functions (as provided).
    :param exclude_readonly: Build a subset model that excludes any readonly fields
    """

    # Fully qualified class name
    fqname = cls.__module__ + "." + cls.__qualname__
    postfix = ""

    def get_name() -> str:
        # If arguments are specified (different from the defaults), we append a hash to the
        # class name, to make it unique
        # We don't check by stack, as cycles get explicitly renamed.
        # When called later, include is explicitly set, so fence passes.
        nonlocal postfix
        is_default = (
            exclude == ()
            and include == ()
            and computed == ()
            and sort_alphabetically is None
            and allow_cycles is None
        )
        hashval = (
            f"{fqname};{exclude};{include};{computed};{_stack}:{sort_alphabetically}:{allow_cycles}"
        )
        postfix = (
            "." + b32encode(sha3_224(hashval.encode("utf-8")).digest()).decode("utf-8").lower()[:6]
            if not is_default
            else ""
        )
        return fqname + postfix

    # We need separate model class for different exclude, include and computed parameters
    _name = name or get_name()
    has_submodel = False

    # Get settings and defaults
    meta = getattr(cls, "PydanticMeta", PydanticMeta)
    default_include: Tuple[str, ...] = tuple(getattr(meta, "include", PydanticMeta.include))
    default_exclude: Tuple[str, ...] = tuple(getattr(meta, "exclude", PydanticMeta.exclude))
    default_computed: Tuple[str, ...] = tuple(getattr(meta, "computed", PydanticMeta.computed))
    max_recursion: int = int(getattr(meta, "max_recursion", PydanticMeta.max_recursion))
    exclude_raw_fields: bool = bool(
        getattr(meta, "exclude_raw_fields", PydanticMeta.exclude_raw_fields)
    )
    _sort_fields: bool = (
        bool(getattr(meta, "sort_alphabetically", PydanticMeta.sort_alphabetically))
        if sort_alphabetically is None
        else sort_alphabetically
    )
    _allow_cycles: bool = bool(
        getattr(meta, "allow_cycles", PydanticMeta.allow_cycles)
        if allow_cycles is None
        else allow_cycles
    )

    # Update parameters with defaults
    include = tuple(include) + default_include
    exclude = tuple(exclude) + default_exclude
    computed = tuple(computed) + default_computed

    # Get all annotations
    annotations = get_annotations(cls)

    # Properties and their annotations` store
    pconfig: Type[pydantic.main.BaseConfig] = type(
        "Config",
        (PydanticModel.Config,),
        {"title": name or cls.__name__, "extra": pydantic.main.Extra.forbid, "fields": {}},
    )
    pannotations: Dict[str, Optional[Type]] = {}
    properties: Dict[str, Any] = {"__annotations__": pannotations, "Config": pconfig}

    # Get model description
    model_description = cls.describe(serializable=False)

    # Field map we use
    field_map: Dict[str, dict] = {}
    pk_raw_field: str = ""

    def field_map_update(keys: tuple, is_relation=True) -> None:
        nonlocal pk_raw_field

        for key in keys:
            fds = model_description[key]
            if isinstance(fds, dict):
                fds = [fds]
            for fd in fds:
                n = fd["name"]
                if key == "pk_field":
                    pk_raw_field = n
                # Include or exclude field
                if (include and n not in include) or n in exclude:
                    continue
                # Remove raw fields
                raw_field = fd.get("raw_field", None)
                if raw_field is not None and exclude_raw_fields and raw_field != pk_raw_field:
                    del field_map[raw_field]
                field_map[n] = fd

    # Update field definitions from description
    if not exclude_readonly:
        field_map_update(("pk_field",), is_relation=False)
    field_map_update(("data_fields",), is_relation=False)
    if not exclude_readonly:
        field_map_update(
            ("fk_fields", "o2o_fields", "m2m_fields", "backward_fk_fields", "backward_o2o_fields")
        )

        # Add possible computed fields
        field_map.update(
            {
                k: {"field_type": callable, "function": getattr(cls, k), "description": None}
                for k in computed
            }
        )

    # Sort field map (Python 3.7+ has guaranteed ordered dictionary keys)
    if _sort_fields:
        # Sort Alphabetically
        field_map = {k: field_map[k] for k in sorted(field_map)}
    else:
        # Sort to definition order
        field_map = {
            k: field_map[k] for k in tuple(cls._meta.fields_map.keys()) + computed if k in field_map
        }

    # Process fields
    for fname, fdesc in field_map.items():
        comment = ""
        fconfig: Dict[str, Any] = {}

        field_type = fdesc["field_type"]
        field_default = fdesc.get("default")

        def get_submodel(_model: "Type[Model]") -> Optional[Type[PydanticModel]]:
            """ Get Pydantic model for the submodel """
            nonlocal exclude, _name, has_submodel

            if _model:
                new_stack = _stack + ((cls, fname, max_recursion),)

                # Get pydantic schema for the submodel
                prefix_len = len(fname) + 1
                pmodel = _pydantic_recursion_protector(
                    _model,
                    exclude=tuple(
                        str(v[prefix_len:]) for v in exclude if v.startswith(fname + ".")
                    ),
                    include=tuple(
                        str(v[prefix_len:]) for v in include if v.startswith(fname + ".")
                    ),
                    computed=tuple(
                        str(v[prefix_len:]) for v in computed if v.startswith(fname + ".")
                    ),
                    stack=new_stack,
                    allow_cycles=_allow_cycles,
                    sort_alphabetically=sort_alphabetically,
                )
            else:
                pmodel = None

            # If the result is None it has been excluded and we need to exclude the field
            if pmodel is None:
                exclude += (fname,)
            else:
                has_submodel = True
            # We need to rename if there are duplicate instances of this model
            if cls in (c[0] for c in _stack):
                _name = name or get_name()

            return pmodel

        # Foreign keys and OneToOne fields are embedded schemas
        if (
            field_type is fields.relational.ForeignKeyFieldInstance
            or field_type is fields.relational.OneToOneFieldInstance
            or field_type is fields.relational.BackwardOneToOneRelation
        ):
            model = get_submodel(fdesc["python_type"])
            if model:
                if fdesc.get("nullable"):
                    fconfig["nullable"] = True
                if fdesc.get("nullable") or field_default is not None:
                    model = Optional[model]  # type: ignore

                pannotations[fname] = model

        # Backward FK and ManyToMany fields are list of embedded schemas
        elif (
            field_type is fields.relational.BackwardFKRelation
            or field_type is fields.relational.ManyToManyFieldInstance
        ):
            model = get_submodel(fdesc["python_type"])
            if model:
                pannotations[fname] = List[model]  # type: ignore

        # Computed fields as methods
        elif field_type is callable:
            func = fdesc["function"]
            annotation = get_annotations(cls, func).get("return", None)
            comment = _cleandoc(func)
            if annotation is not None:
                pannotations[fname] = annotation
        # Json fields
        elif field_type is fields.JSONField:
            pannotations[fname] = Any  # type: ignore
        # Any other tortoise fields
        else:
            annotation = annotations.get(fname, None)
            fconfig.update(fdesc["constraints"])
            ptype = fdesc["python_type"]
            if fdesc.get("nullable"):
                fconfig["nullable"] = True
            if fdesc.get("nullable") or field_default is not None:
                ptype = Optional[ptype]
            if not (exclude_readonly and fdesc["constraints"].get("readOnly") is True):
                pannotations[fname] = annotation or ptype

        # Create a schema for the field
        if fname in pannotations:
            # Use comment if we have and enabled or use the field description if specified
            description = comment or _br_it(fdesc.get("docstring") or fdesc["description"] or "")
            fconfig["description"] = description
            fconfig["title"] = fname.replace("_", " ").title()
            if field_default is not None:
                if callable(field_default):
                    fconfig["default_factory"] = field_default
                    properties[fname] = None
                else:
                    properties[fname] = field_default
            pconfig.fields[fname] = fconfig

    # Here we endure that the name is unique, but complete objects are still labeled verbatim
    if not has_submodel:
        _name = name or f"{fqname}.leaf"
    elif has_submodel:
        _name = name or get_name()

    # Here we de-dup to ensure that a uniquely named object is a unique object
    # This fixes some Pydantic constraints.
    if _name in _MODEL_INDEX:
        return _MODEL_INDEX[_name]

    # Creating Pydantic class for the properties generated before
    model = cast(Type[PydanticModel], type(_name, (PydanticModel,), properties))
    # Copy the Model docstring over
    model.__doc__ = _cleandoc(cls)
    # Store the base class
    setattr(model.__config__, "orig_model", cls)

    # Store model reference so we can de-dup it later on if needed.
    _MODEL_INDEX[_name] = model

    return model


def pydantic_queryset_creator(
    cls: "Type[Model]",
    *,
    name=None,
    exclude: Tuple[str, ...] = (),
    include: Tuple[str, ...] = (),
    computed: Tuple[str, ...] = (),
    allow_cycles: Optional[bool] = None,
    sort_alphabetically: Optional[bool] = None,
) -> Type[PydanticListModel]:
    """
    Function to build a `Pydantic Model <https://pydantic-docs.helpmanual.io/usage/models/>`__ list off Tortoise Model.

    :param cls: The Tortoise Model to put in a list.
    :param name: Specify a custom name explicitly, instead of a generated name.

        The list generated name is currently naive and merely adds a "s" to the end
        of the singular name.
    :param exclude: Extra fields to exclude from the provided model.
    :param include: Extra fields to include from the provided model.
    :param computed: Extra computed fields to include from the provided model.
    :param allow_cycles: Do we allow any cycles in the generated model?
        This is only useful for recursive/self-referential models.

        A value of ``False`` (the default) will prevent any and all backtracking.
    :param sort_alphabetically: Sort the parameters alphabetically instead of Field-definition order.

        The default order would be:

            * Field definition order +
            * order of reverse relations (as discovered) +
            * order of computed functions (as provided).
    """

    submodel = pydantic_model_creator(
        cls,
        exclude=exclude,
        include=include,
        computed=computed,
        allow_cycles=allow_cycles,
        sort_alphabetically=sort_alphabetically,
    )
    lname = name or f"{submodel.__name__}_list"

    properties = {"__annotations__": {"__root__": List[submodel]}}  # type: ignore
    # Creating Pydantic class for the properties generated before
    model = cast(Type[PydanticListModel], type(lname, (PydanticListModel,), properties))
    # Copy the Model docstring over
    model.__doc__ = _cleandoc(cls)
    # The title of the model to hide the hash postfix
    setattr(model.__config__, "title", name or f"{getattr(submodel.__config__,'title')}_list")
    # Store the base class & submodel
    setattr(model.__config__, "submodel", submodel)

    return model
