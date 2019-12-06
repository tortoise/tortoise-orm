import functools
import inspect
import re
import typing
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import tortoise
from tortoise import exceptions, fields, models

if typing.TYPE_CHECKING:
    from tortoise.models import Model


# Pydantic is an optional dependency
try:
    import pydantic
    from pydantic import BaseModel

    @functools.lru_cache()
    def _get_comments(cls: Type["Model"]) -> Dict[str, str]:
        """
        Get comments exactly before attributes

        It can be multiline comment. The placeholder "{model}" will be replaced with the name of the
        model class.

        :param cls: The class we need to extract comments from its source.
        :return: The dictionary of comments by field name
        """
        source = inspect.getsource(cls)
        comments = {}

        for cls in reversed(cls.__mro__):
            if cls is object:
                continue
            matches = re.findall(rf"((?:(?!\n|^)[^\w\n]*#.*?\n)+?)[^\w\n]*(\w+)\s*[:=]", source)
            for match in matches:
                field_name = match[1]
                # Extract text
                comment = re.sub(r"(^\s*#\s*|\s*$)", "", match[0], flags=re.MULTILINE)
                # Class name template
                comment = comment.replace("{model}", cls.__name__)
                # Change multiline texts to HTML
                comments[field_name] = comment.replace("\n", "<br>")

        return comments

    @functools.lru_cache()
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
            if origin is list:
                field_type = field_type.__args__[0]
            # noinspection PyProtectedMember
            if field_name in model_class._meta.fetch_fields and issubclass(
                field_type, PydanticModel
            ):
                subclass_fetch_fields = _get_fetch_fields(
                    field_type, getattr(pydantic_class.__config__, "orig_model")
                )
                if subclass_fetch_fields:
                    fetch_fields.extend([field_name + "__" + f for f in subclass_fetch_fields])
                else:
                    fetch_fields.append(field_name)
        return fetch_fields

    class PydanticModel(BaseModel):
        """ Custom Pydantic BaseModel """

        class Config:
            orm_mode = True  # It should be in ORM mode to convert tortoise data to pydantic

        class Meta:
            # Stores already created pydantic models
            cache: Dict[str, Type["PydanticModel"]] = {}

        @pydantic.validator("*", pre=True, whole=True)  # It is a classmethod!
        def _tortoise_convert(cls, value):  # pylint: disable=E0213
            # Computed fields
            if callable(value):
                return value()
            # Convert ManyToManyRelation to list
            elif isinstance(value, fields.ManyToManyRelation):
                return [v for v in value]
            return value

        @classmethod
        async def from_tortoise(cls, obj: "Model"):
            # Get fields needed to fetch
            fetch_fields = _get_fetch_fields(cls, getattr(cls.__config__, "orig_model"))
            # Fetch fields
            await obj.fetch_related(*fetch_fields)
            # Convert to pydantic object
            values = super().from_orm(obj)
            return values

    def _pydantic_recursion_protector(
        cls: Type["Model"],
        *,
        exclude: Tuple[str] = (),  # type: ignore
        include: Tuple[str] = (),  # type: ignore
        computed: Tuple[str] = (),  # type: ignore
        name=None,
    ) -> Optional[Type[BaseModel]]:
        """
        It is an inner function to protect pydantic model creator against cyclic recursion
        """
        stack = inspect.stack()
        caller_fname = stack[1].frame.f_locals["fname"]  # The field name of the caller
        caller_cls = stack[2].frame.f_locals["cls"]  # The class name of the caller
        prop_path = [caller_fname]  # It stores the fields in the hierarchy
        level = 1
        # Go through the stack to find the cls and fname of the caller
        for frame_info in stack[3:]:
            if frame_info.filename != __file__ and frame_info.filename != models.__file__:
                break
            if frame_info.function == "get_submodel":  # This is the submodel creator function
                # Check recursion level
                frame_max_recursion = frame_info.frame.f_back.f_locals["pydantic_max_recursion"]
                frame_cls = frame_info.frame.f_back.f_locals["cls"]  # The class of the model
                frame_fname = frame_info.frame.f_locals["fname"]  # The name of the field
                prop_path.insert(0, frame_fname)
                if level >= frame_max_recursion:
                    tortoise.logger.warning(
                        "Recursion level %i has reached for model %s",
                        level,
                        frame_cls.__qualname__ + "." + ".".join(prop_path),
                    )
                    return None
                if frame_cls is caller_cls and frame_fname == caller_fname:
                    tortoise.logger.warning(
                        "Recursion detected: %s", frame_cls.__qualname__ + "." + ".".join(prop_path)
                    )
                    return None

                level += 1

        return cls.pydantic_model(exclude=exclude, include=include, computed=computed, name=name)

    def _pydantic_model_creator(
        cls: Type["Model"],
        *,
        exclude: Tuple[str] = (),  # type: ignore
        include: Tuple[str] = (),  # type: ignore
        computed: Tuple[str] = (),  # type: ignore
        name=None,
    ) -> Type[PydanticModel]:
        """
        Inner function to create pydantic model.
        It stores the created models in cache based on arguments
        """
        # Fully qualified class name
        fqname = cls.__module__ + "." + cls.__qualname__

        def get_name() -> str:
            # If arguments are specified (different from the defaults), we append a hash to the
            # class name, to make it unique
            h = (
                ("_" + hex(hash((fqname, exclude, include, computed)))[2:])
                if exclude != () or include != () or computed != ()  # type: ignore
                else ""
            )
            return cls.__name__ + h

        # We need separate model class for different exclude, include and computed parameters
        if not name:
            name = get_name()

        # If we already have this class in cache, use that
        if name in PydanticModel.Meta.cache:
            return PydanticModel.Meta.cache[name]

        # Get defaults
        default_meta = models.Model.Meta
        meta = getattr(cls, "Meta", default_meta)
        default_include = getattr(
            meta, "pydantic_include", getattr(default_meta, "pydantic_include")
        )
        default_exclude = getattr(
            meta, "pydantic_exclude", getattr(default_meta, "pydantic_exclude")
        )
        default_computed = getattr(
            meta, "pydantic_computed", getattr(default_meta, "pydantic_computed")
        )
        backward_relations = getattr(
            meta,
            "pydantic_backward_relations",
            getattr(default_meta, "pydantic_backward_relations"),
        )
        use_comments = getattr(
            meta, "pydantic_use_comments", getattr(default_meta, "pydantic_use_comments")
        )
        # It is used in the recursion protector
        pydantic_max_recursion = getattr(  # noqa: F841
            meta, "pydantic_max_recursion", getattr(default_meta, "pydantic_max_recursion")
        )

        # Update parameters with defaults
        include = include + default_include
        exclude = exclude + default_exclude
        computed = computed + default_computed

        # Get all annotations
        annotations = _get_annotations(cls)
        # Get field comments
        comments = _get_comments(cls) if use_comments else {}

        # Properties and their annotations` store
        properties: Dict[str, Any] = {"__annotations__": {}}

        # Generate field map with relations and computed fields
        field_map = dict(cls._meta.fields_map)  # We need to copy the original to not extend that
        # Add annotated backward relations as well
        field_map.update(
            {
                k: v
                for k, v in annotations.items()
                if k not in field_map
                and hasattr(v, "__origin__")
                and isinstance(v.__origin__, type)
                and issubclass(v.__origin__, (fields.ManyToManyRelation, fields.ReverseRelation))
            }
        )
        # Add possible computed fields
        field_map.update({k: getattr(cls, k) for k in computed})

        # Process fields
        for fname, fval in field_map.items():
            # Include or exclude field
            if include and fname not in include:  # type: ignore
                continue
            if fname in exclude:
                continue

            # The class of the field
            fcls = fval if isinstance(fval, type) else type(fval)  # type: ignore

            # Get annotation for the specific field
            annotation = annotations.get(fname, None)
            annotation_origin = getattr(annotation, "__origin__", type)
            comment = ""

            def model_from_typevar() -> Type["Model"]:
                nonlocal annotation
                try:
                    # ForeignKeyRelation is an union TypeVar, we need the 2nd argument of it, which
                    # is the model
                    if annotation.__origin__ is Union:
                        annotation = annotation.__args__[1]
                    # ManyToManyFieldRelation's 1st argument is the model type
                    elif issubclass(
                        annotation.__origin__, (fields.ReverseRelation, fields.ManyToManyRelation)
                    ):
                        annotation = annotation.__args__[0]
                except AttributeError:  # If annotation has no __origin__
                    raise exceptions.FieldError(
                        f"Annotation error in model '{fqname}' at field '{fname}'!"
                    )
                return annotation

            def get_submodel(_model: Type["Model"]):
                nonlocal exclude, name

                # Get pydantic schema for the submodel
                prefix_len = len(fname) + 1
                pmodel = _pydantic_recursion_protector(
                    _model,
                    exclude=tuple(  # type: ignore
                        [str(v[prefix_len:]) for v in exclude if v.startswith(fname + ".")]
                    ),
                    include=tuple(  # type: ignore
                        [str(v[prefix_len:]) for v in include if v.startswith(fname + ".")]
                    ),
                    computed=tuple(  # type: ignore
                        [str(v[prefix_len:]) for v in computed if v.startswith(fname + ".")]
                    ),
                )

                # We need to add the field into exclude and get new name for the class to cache
                # different model for it
                if pmodel is None:
                    exclude += (fname,)  # type: ignore
                    name = get_name()

                return pmodel

            # Foreign keys are embedded schemas
            if (
                issubclass(
                    fcls, (fields.ForeignKeyField, fields.OneToOneField, fields.ReverseRelation)
                )
                or annotation_origin is Union
            ):
                annotation = annotation or getattr(fval, "field_type", None)
                model = annotation if isinstance(annotation, type) else model_from_typevar()
                model = get_submodel(model)
                if model:
                    properties["__annotations__"][fname] = model

            # ManyToMany fields are list of embedded schemas
            elif annotation and issubclass(annotation_origin, fields.ManyToManyRelation):
                model = model_from_typevar()
                model = get_submodel(model)
                if model:
                    properties["__annotations__"][fname] = List[model]  # type: ignore

            # These are dynamically created backward relation fields, which are not recommended
            # to include
            elif issubclass(fcls, (fields.BackwardFKRelation, fields.ManyToManyFieldInstance)):
                if backward_relations:
                    model = get_submodel(typing.cast(Type["Model"], fval.field_type))
                    if model:
                        properties["__annotations__"][fname] = List[model]  # type: ignore

            # If the annotation is a tortoise model, we need to create a pydantic submodel for it
            # It should be possible only for computed fields
            elif isinstance(annotation, type) and issubclass(annotation, models.Model):
                model = get_submodel(annotation)
                if model:
                    properties["__annotations__"][fname] = model

            # Computed fields as methods
            elif callable(fval):
                annotation = _get_annotations(cls, fval).get("return", None)
                comment = inspect.cleandoc(fval.__doc__).replace("\n", "<br>")  # type: ignore
                if annotation is not None:
                    properties["__annotations__"][fname] = annotation

            # Any other tortoise fields
            else:
                # Try to get annotation for the field, if not specified, we use the
                # tortoise field_type
                properties["__annotations__"][fname] = annotation or fval.field_type

            # Create a schema for the field
            if fname in properties["__annotations__"]:
                comment = comment or comments.get(fname, "")
                properties[fname] = pydantic.Field(
                    None, description=comment, title=fname.replace("_", " ").title()
                )

        # Because of recursion, it is possible to already have the model in cache, then we need
        # to use that
        try:
            model = PydanticModel.Meta.cache[name]
        except KeyError:
            # Creating Pydantic class for the properties generated before
            model = typing.cast(Type[PydanticModel], type(name, (PydanticModel,), properties))
            # The title of the model to not show the hash postfix
            model.__config__.title = cls.__name__  # type: ignore
            # Store the base class
            setattr(model.__config__, "orig_model", cls)
            # Caching model
            PydanticModel.Meta.cache[name] = model

        return model


except ImportError:
    # If pydantic is not installed
    pydantic = None  # type: ignore
    PydanticModel = type  # type: ignore
    _pydantic_model_creator = None  # type: ignore
