import inspect
import re
import typing
from hashlib import sha256
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import pydantic
from pydantic import BaseModel  # pylint: disable=E0611

import tortoise
from tortoise import fields, models

if typing.TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model
    from tortoise.queryset import QuerySet


def _get_comments(cls: Type["Model"]) -> Dict[str, str]:
    """
    Get comments exactly before attributes

    It can be multiline comment. The placeholder "{model}" will be replaced with the name of the
    model class. We require that the comments are in #: (with a colon) format, so you can
    differentiate between private and public comments.

    :param cls: The class we need to extract comments from its source.
    :return: The dictionary of comments by field name
    """
    source = inspect.getsource(cls)
    comments = {}

    for cls in reversed(cls.__mro__):
        if cls is object:
            continue
        matches = re.findall(rf"((?:(?!\n|^)[^\w\n]*#:.*?\n)+?)[^\w\n]*(\w+)\s*[:=]", source)
        for match in matches:
            field_name = match[1]
            # Extract text
            comment = re.sub(r"(^\s*#:\s*|\s*$)", "", match[0], flags=re.MULTILINE)
            # Class name template
            comment = comment.replace("{model}", cls.__name__)
            # Change multiline texts to HTML
            comments[field_name] = comment.replace("\n", "<br>")

    return comments


def _get_annotations(cls: Type["Model"], method: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Get all annotations including base classes
    :param cls: The model class we need annotations from
    :param method: If specified, we try to get the annotations for the callable
    :return: The list of annotations
    """
    globalns = tortoise.Tortoise.apps[cls._meta.app] if cls._meta.app is not None else None
    return typing.get_type_hints(method or cls, globalns=globalns)


def _get_fetch_fields(
    pydantic_class: Type["PydanticModel"], model_class: Type["Model"]
) -> List[str]:
    """
    Recursively collect fields needed to fetch
    :param pydantic_class: The pydantic model class
    :param model_class: The tortoise model class
    :return: The list of fields to be fetched
    """
    fetch_fields = []
    for field_name, field_type in pydantic_class.__annotations__.items():
        origin = getattr(field_type, "__origin__", None)
        if origin in (list, List):
            field_type = field_type.__args__[0]
        # noinspection PyProtectedMember
        if field_name in model_class._meta.fetch_fields and issubclass(field_type, PydanticModel):
            subclass_fetch_fields = _get_fetch_fields(
                field_type, getattr(field_type.__config__, "orig_model")
            )
            if subclass_fetch_fields:
                fetch_fields.extend([field_name + "__" + f for f in subclass_fetch_fields])
            else:
                fetch_fields.append(field_name)
    return fetch_fields


class PydanticModel(BaseModel):
    """ Custom Pydantic BaseModel for Tortoise objects """

    class Config:
        orm_mode = True  # It should be in ORM mode to convert tortoise data to pydantic

    # noinspection PyMethodParameters
    @pydantic.validator("*", pre=True, each_item=False)  # It is a classmethod!
    def _tortoise_convert(cls, value):  # pylint: disable=E0213
        # Computed fields
        if callable(value):
            return value()
        # Convert ManyToManyRelation to list
        elif isinstance(value, (fields.ManyToManyRelation, fields.ReverseRelation)):
            return list(value)
        return value

    @classmethod
    async def from_tortoise_orm(cls, obj: "Model") -> "PydanticModel":
        # Get fields needed to fetch
        fetch_fields = _get_fetch_fields(cls, getattr(cls.__config__, "orig_model"))
        # Fetch fields
        await obj.fetch_related(*fetch_fields)
        # Convert to pydantic object
        values = super().from_orm(obj)
        return values


class PydanticListModel(BaseModel):
    """ Custom Pydantic BaseModel for Tortoise Models """

    @classmethod
    async def from_queryset(cls, queryset: "QuerySet") -> "PydanticListModel":
        submodel = getattr(cls.__config__, "submodel")
        fetch_fields = _get_fetch_fields(submodel, getattr(submodel.__config__, "orig_model"))
        values = cls(
            __root__=[submodel.from_orm(e) for e in await queryset.prefetch_related(*fetch_fields)]
        )
        return values


def _pydantic_recursion_protector(
    cls: Type["Model"],
    *,
    stack: tuple,
    exclude: Tuple[str, ...] = (),
    include: Tuple[str, ...] = (),
    computed: Tuple[str, ...] = (),
    name=None,
    allow_cycles: bool = False,
) -> Optional[Type[PydanticModel]]:
    """
    It is an inner function to protect pydantic model creator against cyclic recursion
    """
    if not allow_cycles and cls in [c[0] for c in stack[:-1]]:
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
        stack=stack,
        allow_cycles=allow_cycles,
    )


def pydantic_model_creator(
    cls: Type["Model"],
    *,
    exclude: Tuple[str, ...] = (),
    include: Tuple[str, ...] = (),
    computed: Tuple[str, ...] = (),
    name=None,
    stack: tuple = (),
    allow_cycles: Optional[bool] = None,
) -> Type[PydanticModel]:
    """
    Inner function to create pydantic model.
    """
    # Fully qualified class name
    fqname = cls.__module__ + "." + cls.__qualname__

    def get_name() -> str:
        # If arguments are specified (different from the defaults), we append a hash to the
        # class name, to make it unique
        # We don't check by stack, as cycles get explicitly renamed.
        # When called later, include is explicitly set, so fence passes.
        h = (
            "_"
            + sha256(
                f"{fqname};{exclude};{include};{computed};{stack}".encode("utf-8")
            ).hexdigest()[:8]
            if exclude != () or include != () or computed != ()
            else ""
        )
        return cls.__name__ + h

    # We need separate model class for different exclude, include and computed parameters
    if not name:
        name = get_name()

    # Get settings and defaults
    default_meta = models.Model.Meta
    meta = getattr(cls, "Meta", default_meta)
    default_include: Tuple[str, ...] = tuple(
        getattr(meta, "pydantic_include", getattr(default_meta, "pydantic_include"))
    )
    default_exclude: Tuple[str, ...] = tuple(
        getattr(meta, "pydantic_exclude", getattr(default_meta, "pydantic_exclude"))
    )
    default_computed: Tuple[str, ...] = tuple(
        getattr(meta, "pydantic_computed", getattr(default_meta, "pydantic_computed"))
    )
    use_comments: bool = bool(
        getattr(meta, "pydantic_use_comments", getattr(default_meta, "pydantic_use_comments"))
    )
    max_recursion: int = int(
        getattr(meta, "pydantic_max_recursion", getattr(default_meta, "pydantic_max_recursion"))
    )
    exclude_raw_fields: bool = bool(
        getattr(
            meta,
            "pydantic_exclude_raw_fields",
            getattr(default_meta, "pydantic_exclude_raw_fields"),
        )
    )
    sort_fields: bool = bool(
        getattr(meta, "pydantic_sort_fields", getattr(default_meta, "pydantic_sort_fields"))
    )
    _allow_cycles: bool = bool(
        getattr(meta, "pydantic_allow_cycles", getattr(default_meta, "pydantic_sort_fields"))
        if allow_cycles is None
        else allow_cycles
    )

    # Update parameters with defaults
    include = tuple(include) + default_include
    exclude = tuple(exclude) + default_exclude
    computed = tuple(computed) + default_computed

    # Get all annotations
    annotations = _get_annotations(cls)
    # Get field comments
    comments = _get_comments(cls) if use_comments else {}

    # Properties and their annotations` store
    properties: Dict[str, Any] = {"__annotations__": {}}

    # Get model description
    model_description = tortoise.Tortoise.describe_model(cls, serializable=False)

    # if not stack:
    #     stack = ((cls, '', max_recursion + 1),)

    # Field map we use
    field_map: Dict[str, dict] = {}

    def field_map_update(keys: tuple, is_relation=True) -> None:
        for key in keys:
            fds = model_description[key]
            if isinstance(fds, dict):
                fds = [fds]
            for fd in fds:
                n = fd["name"]
                # Include or exclude field
                if (include and n not in include) or n in exclude:
                    continue
                # Remove raw fields
                raw_field = fd.get("raw_field", None)
                if raw_field is not None and exclude_raw_fields:
                    del field_map[raw_field]
                field_map[n] = fd

    # Update field definitions from description
    field_map_update(("pk_field", "data_fields"), is_relation=False)
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

    # Sort field map if requested (Python 3.6 has ordered dictionary keys)
    if sort_fields:
        field_map = {k: field_map[k] for k in sorted(field_map)}

    # Process fields
    for fname, fdesc in field_map.items():
        comment = ""

        field_type = fdesc["field_type"]

        def get_submodel(_model: Type["Model"]) -> Optional[Type[PydanticModel]]:
            """ Get Pydantic model for the submodel """
            nonlocal exclude, name

            new_stack = stack + ((cls, fname, max_recursion),)

            # Get pydantic schema for the submodel
            prefix_len = len(fname) + 1
            pmodel = _pydantic_recursion_protector(
                _model,
                exclude=tuple([str(v[prefix_len:]) for v in exclude if v.startswith(fname + ".")]),
                include=tuple([str(v[prefix_len:]) for v in include if v.startswith(fname + ".")]),
                computed=tuple(
                    [str(v[prefix_len:]) for v in computed if v.startswith(fname + ".")]
                ),
                stack=new_stack,
                allow_cycles=_allow_cycles,
            )

            # If the result is None it has been exluded and we need to exclude the field
            if pmodel is None:
                exclude += (fname,)
            # We need to rename if there are duplicate instances of this model
            if cls in [c[0] for c in stack]:
                name = get_name()

            return pmodel

        # Foreign keys and OneToOne fields are embedded schemas
        if (
            field_type is fields.relational.ForeignKeyFieldInstance
            or field_type is fields.relational.OneToOneFieldInstance
            or field_type is fields.relational.BackwardOneToOneRelation
        ):
            model = get_submodel(fdesc["python_type"])
            if model:
                properties["__annotations__"][fname] = model

        # Backward FK and ManyToMany fields are list of embedded schemas
        elif (
            field_type is fields.relational.BackwardFKRelation
            or field_type is fields.relational.ManyToManyFieldInstance
        ):
            model = get_submodel(fdesc["python_type"])
            if model:
                properties["__annotations__"][fname] = List[model]  # type: ignore

        # Computed fields as methods
        elif field_type is callable:
            func = fdesc["function"]
            annotation = _get_annotations(cls, func).get("return", None)
            comment = inspect.cleandoc(func.__doc__).replace("\n", "<br>")
            if annotation is not None:
                properties["__annotations__"][fname] = annotation

        # Any other tortoise fields
        else:
            annotation = annotations.get(fname, None)
            properties["__annotations__"][fname] = annotation or fdesc["python_type"]

        # Create a schema for the field
        if fname in properties["__annotations__"]:
            # Use comment if we have and enabled or use the field description if specified
            description = comment or comments.get(fname, "") or fdesc["description"]
            properties[fname] = pydantic.Field(
                None, description=description, title=fname.replace("_", " ").title()
            )

    # Creating Pydantic class for the properties generated before
    model = typing.cast(Type[PydanticModel], type(name, (PydanticModel,), properties))
    # Copy the Model docstring over
    model.__doc__ = (cls.__doc__ or "").strip()
    # The title of the model to hide the hash postfix
    setattr(model.__config__, "title", cls.__name__)
    # Store the base class
    setattr(model.__config__, "orig_model", cls)

    return model


def pydantic_queryset_creator(
    cls: Type["Model"],
    *,
    exclude: Tuple[str, ...] = (),
    include: Tuple[str, ...] = (),
    computed: Tuple[str, ...] = (),
    name=None,
    allow_cycles: bool = False,
) -> Type[PydanticListModel]:

    submodel = pydantic_model_creator(
        cls, exclude=exclude, include=include, computed=computed, allow_cycles=allow_cycles
    )
    lname = name or f"{submodel.__name__}s"

    properties = {"__annotations__": {"__root__": List[submodel]}}  # type: ignore
    # Creating Pydantic class for the properties generated before
    model = typing.cast(Type[PydanticListModel], type(lname, (PydanticListModel,), properties))
    # Copy the Model docstring over
    model.__doc__ = (cls.__doc__ or "").strip()
    # The title of the model to hide the hash postfix
    setattr(model.__config__, "title", lname)
    # Store the base class & submodel
    setattr(model.__config__, "submodel", submodel)

    return model
