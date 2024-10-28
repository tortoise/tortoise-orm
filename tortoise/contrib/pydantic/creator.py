import dataclasses
import inspect
import sys
from base64 import b32encode
from typing import MutableMapping

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from dataclasses import dataclass, field
from hashlib import sha3_224
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Callable, Union, TypeVar

from pydantic import ConfigDict, Field, computed_field, create_model
from pydantic._internal._decorators import PydanticDescriptorProxy

from tortoise.contrib.pydantic.base import PydanticListModel, PydanticModel
from tortoise.contrib.pydantic.utils import get_annotations
from tortoise.fields import IntField, JSONField, TextField
from tortoise.contrib.pydantic.dataclasses import FieldDescriptionBase, ForeignKeyFieldInstanceDescription, \
    OneToOneFieldInstanceDescription, BackwardOneToOneRelationDescription, BackwardFKRelationDescription, \
    ManyToManyFieldInstanceDescription, describe_model_by_dataclass, ModelDescription

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model

_MODEL_INDEX: Dict[str, Type[PydanticModel]] = {}


@dataclass
class PydanticMetaData:
    #: If not empty, only fields this property contains will be in the pydantic model
    include: Tuple[str, ...] = ()

    #: Fields listed in this property will be excluded from pydantic model
    exclude: Tuple[str, ...] = field(default_factory=lambda: ("Meta",))

    #: Computed fields can be listed here to use in pydantic model
    computed: Tuple[str, ...] = field(default_factory=tuple)

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

    #: Allows user to specify custom config for generated model
    model_config: Optional[ConfigDict] = None

    @classmethod
    def from_pydantic_meta(cls, old_pydantic_meta: Any):
        default_meta = cls()

        def get_param_from_pydantic_meta(attr: str, default: Any) -> Any:
            return getattr(old_pydantic_meta, attr, default)
        include = tuple(get_param_from_pydantic_meta("include", default_meta.include))
        exclude = tuple(get_param_from_pydantic_meta("exclude", default_meta.exclude))
        computed = tuple(get_param_from_pydantic_meta("computed", default_meta.computed))
        backward_relations = bool(
            get_param_from_pydantic_meta("backward_relations_raw", default_meta.backward_relations)
        )
        max_recursion = int(get_param_from_pydantic_meta("max_recursion", default_meta.max_recursion))
        allow_cycles = bool(get_param_from_pydantic_meta("allow_cycles", default_meta.allow_cycles))
        exclude_raw_fields = bool(
            get_param_from_pydantic_meta("exclude_raw_fields", default_meta.exclude_raw_fields)
        )
        sort_alphabetically = bool(
            get_param_from_pydantic_meta("sort_alphabetically", default_meta.sort_alphabetically)
        )
        model_config = get_param_from_pydantic_meta("model_config", default_meta.model_config)
        return PydanticMetaData(
            include=include,
            exclude=exclude,
            computed=computed,
            backward_relations=backward_relations,
            max_recursion=max_recursion,
            allow_cycles=allow_cycles,
            exclude_raw_fields=exclude_raw_fields,
            sort_alphabetically=sort_alphabetically,
            model_config=model_config
        )

    def construct_pydantic_meta(
            self,
            meta_override: Type
    ) -> Self:
        def get_param_from_meta_override(attr: str) -> Any:
            return getattr(meta_override, attr, getattr(self, attr))

        default_include: Tuple[str, ...] = tuple(get_param_from_meta_override("include"))
        default_exclude: Tuple[str, ...] = tuple(get_param_from_meta_override("exclude"))
        default_computed: Tuple[str, ...] = tuple(get_param_from_meta_override("computed"))
        default_config: Optional[ConfigDict] = self.model_config

        backward_relations: bool = bool(get_param_from_meta_override("backward_relations"))

        max_recursion: int = int(get_param_from_meta_override("max_recursion"))
        exclude_raw_fields: bool = bool(get_param_from_meta_override("exclude_raw_fields"))
        sort_alphabetically: bool = bool(get_param_from_meta_override("sort_alphabetically"))
        allow_cycles: bool = bool(get_param_from_meta_override("allow_cycles"))

        return PydanticMetaData(
            include=default_include,
            exclude=default_exclude,
            computed=default_computed,
            model_config=default_config,
            backward_relations=backward_relations,
            max_recursion=max_recursion,
            exclude_raw_fields=exclude_raw_fields,
            sort_alphabetically=sort_alphabetically,
            allow_cycles=allow_cycles
        )

    def finalize_meta(
            self,
            exclude: Tuple[str, ...] = (),
            include: Tuple[str, ...] = (),
            computed: Tuple[str, ...] = (),
            allow_cycles: Optional[bool] = None,
            sort_alphabetically: Optional[bool] = None,
            model_config: Optional[ConfigDict] = None,
    ) -> Self:
        _sort_fields: bool = (
            self.sort_alphabetically
            if sort_alphabetically is None
            else sort_alphabetically
        )
        _allow_cycles: bool = (
            self.allow_cycles
            if allow_cycles is None
            else allow_cycles
        )

        include = tuple(include) + self.include
        exclude = tuple(exclude) + self.exclude
        computed = tuple(computed) + self.computed

        _model_config = ConfigDict()
        if self.model_config:
            _model_config.update(self.model_config)
        if model_config:
            _model_config.update(model_config)

        return PydanticMetaData(
            include=include,
            exclude=exclude,
            computed=computed,
            backward_relations=self.backward_relations,
            max_recursion=self.max_recursion,
            exclude_raw_fields=self.exclude_raw_fields,
            sort_alphabetically=_sort_fields,
            allow_cycles=_allow_cycles,
            model_config=_model_config
        )


def _br_it(val: str) -> str:
    return val.replace("\n", "<br/>").strip()


def _cleandoc(obj: Any) -> str:
    return _br_it(inspect.cleandoc(obj.__doc__ or ""))


def _pydantic_recursion_protector(
        cls: "Type[Model]",
        *,
        stack: Tuple,
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
    pmc = PydanticModelCreator(
        cls,
        exclude=exclude,
        include=include,
        computed=computed,
        name=name,
        _stack=stack,
        allow_cycles=allow_cycles,
        sort_alphabetically=sort_alphabetically,
        _as_submodel=True,
    )
    return pmc.create_pydantic_model()


@dataclasses.dataclass
class ComputedFieldDescription:
    field_type: Any
    function: Callable[[], Any]
    description: Optional[str]


FieldDescriptionT = TypeVar('FieldDescriptionT', bound=FieldDescriptionBase)


class FieldMap(MutableMapping[str, Union[FieldDescriptionBase, ComputedFieldDescription]]):
    def __init__(self, meta: PydanticMetaData, pk_field_description: Optional[FieldDescriptionBase] = None):
        self._field_map: Dict[str, Union[FieldDescriptionBase, ComputedFieldDescription]] = {}
        self.pk_raw_field = pk_field_description.name if pk_field_description is not None else ""
        if pk_field_description:
            self.pk_raw_field = pk_field_description.name
            self.field_map_update([pk_field_description], meta)
        self.computed_fields: Dict[str, ComputedFieldDescription] = {}

    def __delitem__(self, __key):
        self._field_map.__delitem__(__key)

    def __getitem__(self, __key):
        return self._field_map.__getitem__(__key)

    def __len__(self):  # pragma: no-coverage
        return self._field_map.__len__()

    def __iter__(self):
        return self._field_map.__iter__()

    def __setitem__(self, __key, __value):
        self._field_map.__setitem__(__key, __value)

    def sort_alphabetically(self) -> None:
        self._field_map = {k: self._field_map[k] for k in sorted(self._field_map)}

    def sort_definition_order(self, cls: "Type[Model]", computed: Tuple[str, ...]) -> None:
        self._field_map = {
            k: self._field_map[k] for k in tuple(cls._meta.fields_map.keys()) + computed if k in self._field_map
        }

    def field_map_update(self, field_descriptions: List[FieldDescriptionT], meta: PydanticMetaData) -> None:
        for field_description in field_descriptions:
            name = field_description.name
            # Include or exclude field
            if (meta.include and name not in meta.include) or name in meta.exclude:
                continue
            # Remove raw fields
            if isinstance(field_description, ForeignKeyFieldInstanceDescription):
                raw_field = field_description.raw_field
                if raw_field is not None and meta.exclude_raw_fields and raw_field != self.pk_raw_field:
                    self.pop(raw_field, None)
            self[name] = field_description

    def computed_field_map_update(self, computed: Tuple[str, ...], cls: "Type[Model]"):
        self._field_map.update(
            {
                k: ComputedFieldDescription(
                    field_type=callable,
                    function=getattr(cls, k),
                    description=None,
                )
                for k in computed
            }
        )


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
        name=name,
    )
    lname = name or f"{submodel.__name__}_list"

    # Creating Pydantic class for the properties generated before
    model = create_model(
        lname,
        __base__=PydanticListModel,
        root=(List[submodel], Field(default_factory=list)),  # type: ignore
    )
    # Copy the Model docstring over
    model.__doc__ = _cleandoc(cls)
    # The title of the model to hide the hash postfix
    model.model_config["title"] = name or f"{submodel.model_config['title']}_list"
    model.model_config["submodel"] = submodel  # type: ignore
    return model


class PydanticModelCreator:
    def __init__(
            self,
            cls: "Type[Model]",
            name: Optional[str] = None,
            exclude: Optional[Tuple[str, ...]] = None,
            include: Optional[Tuple[str, ...]] = None,
            computed: Optional[Tuple[str, ...]] = None,
            optional: Optional[Tuple[str, ...]] = None,
            allow_cycles: Optional[bool] = None,
            sort_alphabetically: Optional[bool] = None,
            exclude_readonly: bool = False,
            meta_override: Optional[Type] = None,
            model_config: Optional[ConfigDict] = None,
            validators: Optional[Dict[str, Any]] = None,
            module: str = __name__,
            _stack: tuple = (),
            _as_submodel: bool = False
    ) -> None:
        self._cls: "Type[Model]" = cls
        self._stack: Tuple[Tuple["Type[Model]", str, int], ...] = tuple()  # ((Type[Model], field_name, max_recursion),)
        self._is_default: bool = (
                exclude is None
                and include is None
                and computed is None
                and optional is None
                and sort_alphabetically is None
                and allow_cycles is None
                and meta_override is None
                and not exclude_readonly
        )
        if exclude is None:
            exclude = ()
        if include is None:
            include = ()
        if computed is None:
            computed = ()
        if optional is None:
            optional = ()

        if meta := getattr(cls, "PydanticMeta", None):
            meta_from_class = PydanticMetaData.from_pydantic_meta(meta)
        else:  # default
            meta_from_class = PydanticMetaData()
        if meta_override:
            meta_from_class = meta_from_class.construct_pydantic_meta(meta_override)
        self.meta = meta_from_class.finalize_meta(
            exclude, include, computed, allow_cycles, sort_alphabetically, model_config
        )

        self._exclude_read_only: bool = exclude_readonly

        self._fqname = cls.__module__ + "." + cls.__qualname__
        self._name: str
        self._title: str
        self.given_name = name

        self._as_submodel = _as_submodel

        self._annotations = get_annotations(cls)

        self._pconfig: ConfigDict

        self._properties: Dict[str, Any] = dict()

        self._model_description: ModelDescription = describe_model_by_dataclass(cls)

        self._field_map: FieldMap = self.initialize_field_map()
        self.construct_field_map()

        self._optional = optional

        self._validators = validators
        self._module = module

        self._stack = _stack

    def get_name(self) -> Tuple[str, str]:
        # If arguments are specified (different from the defaults), we append a hash to the
        # class name, to make it unique
        # We don't check by stack, as cycles get explicitly renamed.
        # When called later, include is explicitly set, so fence passes.
        if self.given_name is not None:
            return self.given_name, self.given_name
        hashval = (
            f"{self._fqname};{self.meta.exclude};{self.meta.include};{self.meta.computed};"
            f"{self.meta.sort_alphabetically}:{self.meta.allow_cycles}:{self._exclude_read_only}"
        )
        postfix = (
            ":" + b32encode(sha3_224(hashval.encode("utf-8")).digest()).decode("utf-8").lower()[:6]
            if not self._is_default
            else ""
        )
        return self._fqname + postfix, self._cls.__name__

    def initialize_pconfig(self) -> ConfigDict:
        pconfig: ConfigDict = PydanticModel.model_config.copy()
        if self.meta.model_config:
            pconfig.update(self.meta.model_config)
        if "title" not in pconfig:
            pconfig["title"] = self._title
        if "extra" not in pconfig:
            pconfig["extra"] = 'forbid'
        return pconfig

    def initialize_field_map(self) -> FieldMap:
        return FieldMap(self.meta) \
            if self._exclude_read_only \
            else FieldMap(self.meta, pk_field_description=self._model_description.pk_field)

    def construct_field_map(self) -> None:
        self._field_map.field_map_update(field_descriptions=self._model_description.data_fields, meta=self.meta)
        if not self._exclude_read_only:
            for field_descriptions in (
                    self._model_description.fk_fields,
                    self._model_description.o2o_fields,
                    self._model_description.m2m_fields
            ):
                self._field_map.field_map_update(field_descriptions, self.meta)
            if self.meta.backward_relations:
                for field_descriptions in (
                        self._model_description.backward_fk_fields,
                        self._model_description.backward_o2o_fields
                ):
                    self._field_map.field_map_update(field_descriptions, self.meta)
            self._field_map.computed_field_map_update(self.meta.computed, self._cls)
        if self.meta.sort_alphabetically:
            self._field_map.sort_alphabetically()
        else:
            self._field_map.sort_definition_order(self._cls, self.meta.computed)

    def create_pydantic_model(self) -> Type[PydanticModel]:
        for field_name, field_description in self._field_map.items():
            self.process_field(field_name, field_description)

        self._name, self._title = self.get_name()
        if self._as_submodel and self._stack:
            self._name = f"{self._name}:leaf"

        if self._name in _MODEL_INDEX:
            return _MODEL_INDEX[self._name]

        self._pconfig = self.initialize_pconfig()
        self._properties["model_config"] = self._pconfig
        model = create_model(
            self._name,
            __base__=PydanticModel,
            __module__=self._module,
            __validators__=self._validators,
            **self._properties,
        )
        # Copy the Model docstring over
        model.__doc__ = _cleandoc(self._cls)
        # Store the base class
        model.model_config["orig_model"] = self._cls  # type: ignore
        # Store model reference so we can de-dup it later on if needed.
        _MODEL_INDEX[self._name] = model
        return model

    def process_field(
            self,
            field_name: str,
            field_description: Union[FieldDescriptionBase, ComputedFieldDescription],
    ) -> None:
        json_schema_extra: Dict[str, Any] = {}
        fconfig: Dict[str, Any] = {
            "json_schema_extra": json_schema_extra,
        }
        field_property: Optional[Any] = None
        is_to_one_relation: bool = False
        comment = ""
        if isinstance(field_description, FieldDescriptionBase):
            field_property, is_to_one_relation = self.process_normal_field_description(
                field_name, field_description, json_schema_extra, fconfig
            )
        elif isinstance(field_description, ComputedFieldDescription):
            field_property, is_to_one_relation = self.process_computed_field_description(field_description), False
            comment = _cleandoc(field_description.function)

        if field_property:
            self._properties[field_name] = field_property
        if field_name in self._properties and not isinstance(self._properties[field_name], tuple):
            fconfig["title"] = field_name.replace("_", " ").title()
            description = comment or _br_it(field_description.docstring or field_description.description or "") \
                if isinstance(field_description, FieldDescriptionBase) \
                else (comment or _br_it(field_description.description or ""))
            if description:
                fconfig["description"] = description
            ftype = self._properties[field_name]
            if not isinstance(ftype, PydanticDescriptorProxy) and isinstance(field_description, FieldDescriptionBase):
                if (
                        field_name in self._optional
                        or (field_description.default is not None and not callable(field_description.default))
                ):
                    self._properties[field_name] = (ftype, Field(default=field_description.default, **fconfig))
                else:
                    if (
                            (
                                    json_schema_extra.get("nullable")
                                    and not is_to_one_relation
                                    and field_description.field_type not in (IntField, TextField)
                            )
                            or (self._exclude_read_only and json_schema_extra.get("readOnly"))
                    ):
                        fconfig["default_factory"] = lambda: None
                    self._properties[field_name] = (ftype, Field(**fconfig))

    def process_normal_field_description(
            self,
            field_name: str,
            field_description: FieldDescriptionBase,
            json_schema_extra: Dict[str, Any],
            fconfig: Dict[str, Any],
    ) -> Tuple[Optional[Any], bool]:
        if isinstance(field_description, (BackwardFKRelationDescription, ManyToManyFieldInstanceDescription)):
            return self.process_many_field_relation(field_name, field_description), False
        elif isinstance(
                field_description,
                (
                        ForeignKeyFieldInstanceDescription,
                        OneToOneFieldInstanceDescription,
                        BackwardOneToOneRelationDescription
                )
        ):
            return self.process_single_field_relation(field_name, field_description, json_schema_extra), True
        elif field_description.field_type is JSONField:
            return self.process_json_field_description(), False
        return self.process_data_field_description(field_name, field_description, json_schema_extra, fconfig), False

    def process_single_field_relation(
            self,
            field_name: str,
            field_description: Union[
                ForeignKeyFieldInstanceDescription,
                OneToOneFieldInstanceDescription,
                BackwardOneToOneRelationDescription
            ],
            json_schema_extra: Dict[str, Any],
    ) -> Optional[Type[PydanticModel]]:
        model: Optional[Type[PydanticModel]] = self.get_submodel(field_description.python_type, field_name)
        if model:
            if field_description.nullable:
                json_schema_extra["nullable"] = True
            if field_description.nullable or field_description.default is not None:
                model = Optional[model]  # type: ignore

            return model
        return None

    def process_many_field_relation(
            self,
            field_name: str,
            field_description: Union[BackwardFKRelationDescription, ManyToManyFieldInstanceDescription],
    ) -> Optional[Type[List[Type[PydanticModel]]]]:
        model = self.get_submodel(field_description.python_type, field_name)
        if model:
            return List[model]  # type: ignore
        return None

    def process_json_field_description(self) -> Any:
        return Any

    def process_data_field_description(
            self,
            field_name: str,
            field_description: FieldDescriptionBase,
            json_schema_extra: Dict[str, Any],
            fconfig: Dict[str, Any],
    ) -> Optional[Any]:
        annotation = self._annotations.get(field_name, None)
        if "readOnly" in field_description.constraints:
            json_schema_extra["readOnly"] = field_description.constraints["readOnly"]
            del field_description.constraints["readOnly"]
        fconfig.update(field_description.constraints)
        ptype = field_description.python_type
        if field_description.nullable:
            json_schema_extra["nullable"] = True
        if field_name in self._optional or field_description.default is not None or field_description.nullable:
            ptype = Optional[ptype]  # type: ignore
        if not (self._exclude_read_only and json_schema_extra.get("readOnly") is True):
            return annotation or ptype
        return None

    def process_computed_field_description(
            self,
            field_description: ComputedFieldDescription,
    ) -> Optional[Any]:
        func = field_description.function
        annotation = get_annotations(self._cls, func).get("return", None)
        comment = _cleandoc(func)
        if annotation is not None:
            c_f = computed_field(return_type=annotation, description=comment)
            ret = c_f(func)
            return ret
        return None

    def get_submodel(self, _model: Optional["Type[Model]"], field_name: str) -> Optional[Type[PydanticModel]]:
        """Get Pydantic model for the submodel"""

        if _model:
            new_stack = self._stack + ((self._cls, field_name, self.meta.max_recursion),)

            # Get pydantic schema for the submodel
            prefix_len = len(field_name) + 1
            pmodel = _pydantic_recursion_protector(
                _model,
                exclude=tuple(
                    str(v[prefix_len:]) for v in self.meta.exclude if v.startswith(field_name + ".")
                ),
                include=tuple(
                    str(v[prefix_len:]) for v in self.meta.include if v.startswith(field_name + ".")
                ),
                computed=tuple(
                    str(v[prefix_len:]) for v in self.meta.computed if v.startswith(field_name + ".")
                ),
                stack=new_stack,
                allow_cycles=self.meta.allow_cycles,
                sort_alphabetically=self.meta.sort_alphabetically,
            )
        else:
            pmodel = None

        # If the result is None it has been excluded and we need to exclude the field
        if pmodel is None:
            self.meta.exclude += (field_name,)

        return pmodel


def pydantic_model_creator(
        cls: "Type[Model]",
        *,
        name=None,
        exclude: Optional[Tuple[str, ...]] = None,
        include: Optional[Tuple[str, ...]] = None,
        computed: Optional[Tuple[str, ...]] = None,
        optional: Optional[Tuple[str, ...]] = None,
        allow_cycles: Optional[bool] = None,
        sort_alphabetically: Optional[bool] = None,
        _stack: tuple = (),
        exclude_readonly: bool = False,
        meta_override: Optional[Type] = None,
        model_config: Optional[ConfigDict] = None,
        validators: Optional[Dict[str, Any]] = None,
        module: str = __name__,
) -> Type[PydanticModel]:
    pmc = PydanticModelCreator(
        cls=cls,
        name=name,
        exclude=exclude,
        include=include,
        computed=computed,
        optional=optional,
        allow_cycles=allow_cycles,
        sort_alphabetically=sort_alphabetically,
        exclude_readonly=exclude_readonly,
        meta_override=meta_override,
        model_config=model_config,
        validators=validators,
        module=module
    )
    return pmc.create_pydantic_model()
