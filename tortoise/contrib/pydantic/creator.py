import inspect
from base64 import b32encode
from copy import copy
from hashlib import sha3_224
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic import ConfigDict
from pydantic import Field as PydanticField
from pydantic import computed_field, create_model

from tortoise import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)
from tortoise.contrib.pydantic.base import PydanticListModel, PydanticModel
from tortoise.contrib.pydantic.descriptions import (
    ComputedFieldDescription,
    ModelDescription,
    PydanticMetaData,
)
from tortoise.contrib.pydantic.utils import get_annotations
from tortoise.fields import Field, JSONField

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model

_MODEL_INDEX: Dict[str, Type[PydanticModel]] = {}
"""
The index works as follows:
1. the hash is calculated from the following:
    - the fully qualified name of the model
    - the names of the contained fields
    - the names of all relational fields and the corresponding names of the pydantic model.
      This is because if the model is not yet fully initialized, the relational fields are not yet present.
2. the hash does not take into account the resulting name of the model; this must be checked separately.
3. the hash can only be calculated after a complete analysis of the given model.
"""


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


class FieldMap(MutableMapping[str, Union[Field, ComputedFieldDescription]]):
    def __init__(self, meta: PydanticMetaData, pk_field: Optional[Field] = None):
        self._field_map: Dict[str, Union[Field, ComputedFieldDescription]] = {}
        self.pk_raw_field = pk_field.model_field_name if pk_field is not None else ""
        if pk_field:
            self.pk_raw_field = pk_field.model_field_name
            self.field_map_update([pk_field], meta)
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
            k: self._field_map[k]
            for k in tuple(cls._meta.fields_map.keys()) + computed
            if k in self._field_map
        }

    def field_map_update(self, fields: List[Field], meta: PydanticMetaData) -> None:
        for field in fields:
            name = field.model_field_name
            # Include or exclude field
            if (meta.include and name not in meta.include) or name in meta.exclude:
                continue
            # Remove raw fields
            if isinstance(field, ForeignKeyFieldInstance):
                raw_field = field.source_field
                if (
                    raw_field is not None
                    and meta.exclude_raw_fields
                    and raw_field != self.pk_raw_field
                ):
                    self.pop(raw_field, None)
            self[name] = field

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
    Function to build a `Pydantic Model <https://docs.pydantic.dev/latest/concepts/models/>`__ list off Tortoise Model.

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
        root=(List[submodel], PydanticField(default_factory=list)),  # type: ignore
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
        _as_submodel: bool = False,
    ) -> None:
        self._cls: "Type[Model]" = cls
        self._stack: Tuple[Tuple["Type[Model]", str, int], ...] = (
            _stack  # ((Type[Model], field_name, max_recursion),)
        )
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
            exclude=exclude,
            include=include,
            computed=computed,
            allow_cycles=allow_cycles,
            sort_alphabetically=sort_alphabetically,
            model_config=model_config,
        )

        self._exclude_read_only: bool = exclude_readonly

        self._fqname = cls.__module__ + "." + cls.__qualname__
        self._name: str
        self._title: str
        self.given_name = name
        self.__hash: str = ""

        self._as_submodel = _as_submodel

        self._annotations = get_annotations(cls)

        self._pconfig: ConfigDict

        self._properties: Dict[str, Any] = dict()
        self._relational_fields_index: List[Tuple[str, str]] = list()

        self._model_description: ModelDescription = ModelDescription.from_model(cls)

        self._field_map: FieldMap = self._initialize_field_map()
        self._construct_field_map()

        self._optional = optional

        self._validators = validators
        self._module = module

        self._stack = _stack

    @property
    def _hash(self):
        if self.__hash == "":
            hashval = (
                f"{self._fqname};{self._properties.keys()};{self._relational_fields_index};{self._optional};"
                f"{self.meta.allow_cycles}"
            )
            self.__hash = (
                b32encode(sha3_224(hashval.encode("utf-8")).digest()).decode("utf-8").lower()[:6]
            )
        return self.__hash

    def get_name(self) -> Tuple[str, str]:
        # If arguments are specified (different from the defaults), we append a hash to the
        # class name, to make it unique
        # We don't check by stack, as cycles get explicitly renamed.
        # When called later, include is explicitly set, so fence passes.
        if self.given_name is not None:
            return self.given_name, self.given_name
        name = f"{self._fqname}:{self._hash}" if not self._is_default else self._fqname
        name = f"{name}:leaf" if self._as_submodel else name
        return name, self._cls.__name__

    def _initialize_pconfig(self) -> ConfigDict:
        pconfig: ConfigDict = PydanticModel.model_config.copy()
        if self.meta.model_config:
            pconfig.update(self.meta.model_config)
        if "title" not in pconfig:
            pconfig["title"] = self._title
        if "extra" not in pconfig:
            pconfig["extra"] = "forbid"
        return pconfig

    def _initialize_field_map(self) -> FieldMap:
        return (
            FieldMap(self.meta)
            if self._exclude_read_only
            else FieldMap(self.meta, pk_field=self._model_description.pk_field)
        )

    def _construct_field_map(self) -> None:
        self._field_map.field_map_update(fields=self._model_description.data_fields, meta=self.meta)
        if not self._exclude_read_only:
            for fields in (
                self._model_description.fk_fields,
                self._model_description.o2o_fields,
                self._model_description.m2m_fields,
            ):
                self._field_map.field_map_update(fields, self.meta)
            if self.meta.backward_relations:
                for fields in (
                    self._model_description.backward_fk_fields,
                    self._model_description.backward_o2o_fields,
                ):
                    self._field_map.field_map_update(fields, self.meta)
            self._field_map.computed_field_map_update(self.meta.computed, self._cls)
        if self.meta.sort_alphabetically:
            self._field_map.sort_alphabetically()
        else:
            self._field_map.sort_definition_order(self._cls, self.meta.computed)

    def create_pydantic_model(self) -> Type[PydanticModel]:
        for field_name, field in self._field_map.items():
            self._process_field(field_name, field)

        self._name, self._title = self.get_name()

        if self._hash in _MODEL_INDEX:
            # there is a model exactly the same, but the name could be different
            hashed_model = _MODEL_INDEX[self._hash]
            if hashed_model.__name__ == self._name:
                # also the same name
                return _MODEL_INDEX[self._hash]

        self._pconfig = self._initialize_pconfig()
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
        _MODEL_INDEX[self._hash] = model
        return model

    def _process_field(
        self,
        field_name: str,
        field: Union[Field, ComputedFieldDescription],
    ) -> None:
        json_schema_extra: Dict[str, Any] = {}
        fconfig: Dict[str, Any] = {
            "json_schema_extra": json_schema_extra,
        }
        field_property: Optional[Any] = None
        is_to_one_relation: bool = False
        if isinstance(field, Field):
            field_property, is_to_one_relation = self._process_normal_field(
                field_name, field, json_schema_extra, fconfig
            )
            if field_property:
                fconfig["title"] = field_name.replace("_", " ").title()
                description = _br_it(field.docstring or field.description or "")
                if description:
                    fconfig["description"] = description
                if field_name in self._optional or (
                    field.default is not None and not callable(field.default)
                ):
                    self._properties[field_name] = (
                        field_property,
                        PydanticField(default=field.default, **fconfig),
                    )
                else:
                    if (json_schema_extra.get("nullable") and not is_to_one_relation) or (
                        self._exclude_read_only and json_schema_extra.get("readOnly")
                    ):
                        # see: https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields
                        fconfig["default"] = None
                    self._properties[field_name] = (field_property, PydanticField(**fconfig))
        elif isinstance(field, ComputedFieldDescription):
            field_property, is_to_one_relation = self._process_computed_field(field), False
            if field_property:
                comment = _cleandoc(field.function)
                fconfig["title"] = field_name.replace("_", " ").title()
                description = comment or _br_it(field.description or "")
                if description:
                    fconfig["description"] = description
                self._properties[field_name] = field_property

    def _process_normal_field(
        self,
        field_name: str,
        field: Field,
        json_schema_extra: Dict[str, Any],
        fconfig: Dict[str, Any],
    ) -> Tuple[Optional[Any], bool]:
        if isinstance(
            field, (ForeignKeyFieldInstance, OneToOneFieldInstance, BackwardOneToOneRelation)
        ):
            return self._process_single_field_relation(field_name, field, json_schema_extra), True
        elif isinstance(field, (BackwardFKRelation, ManyToManyFieldInstance)):
            return self._process_many_field_relation(field_name, field), False
        elif field.field_type is JSONField:
            return Any, False
        return self._process_data_field(field_name, field, json_schema_extra, fconfig), False

    def _process_single_field_relation(
        self,
        field_name: str,
        field: Union[ForeignKeyFieldInstance, OneToOneFieldInstance, BackwardOneToOneRelation],
        json_schema_extra: Dict[str, Any],
    ) -> Optional[Type[PydanticModel]]:
        python_type = getattr(field, "related_model", field.field_type)
        model: Optional[Type[PydanticModel]] = self._get_submodel(python_type, field_name)
        if model:
            self._relational_fields_index.append((field_name, model.__name__))
            if field.null:
                json_schema_extra["nullable"] = True
            if field.null or field.default is not None:
                model = Optional[model]  # type: ignore

            return model
        return None

    def _process_many_field_relation(
        self,
        field_name: str,
        field: Union[BackwardFKRelation, ManyToManyFieldInstance],
    ) -> Optional[Type[List[Type[PydanticModel]]]]:
        python_type = field.related_model
        model = self._get_submodel(python_type, field_name)
        if model:
            self._relational_fields_index.append((field_name, model.__name__))
            return List[model]  # type: ignore
        return None

    def _process_data_field(
        self,
        field_name: str,
        field: Field,
        json_schema_extra: Dict[str, Any],
        fconfig: Dict[str, Any],
    ) -> Optional[Any]:
        annotation = self._annotations.get(field_name, None)
        constraints = copy(field.constraints)
        if "readOnly" in constraints:
            json_schema_extra["readOnly"] = constraints["readOnly"]
            del constraints["readOnly"]
        fconfig.update(constraints)
        python_type = getattr(field, "related_model", field.field_type)
        ptype = python_type
        if field.null:
            json_schema_extra["nullable"] = True
        if not field.pk and (
            field_name in self._optional or field.default is not None or field.null
        ):
            ptype = Optional[ptype]
        if not (self._exclude_read_only and json_schema_extra.get("readOnly") is True):
            return annotation or ptype
        return None

    def _process_computed_field(
        self,
        field: ComputedFieldDescription,
    ) -> Optional[Any]:
        func = field.function
        annotation = get_annotations(self._cls, func).get("return", None)
        comment = _cleandoc(func)
        if annotation is not None:
            c_f = computed_field(return_type=annotation, description=comment)
            ret = c_f(func)
            return ret
        return None

    def _get_submodel(
        self, _model: Optional["Type[Model]"], field_name: str
    ) -> Optional[Type[PydanticModel]]:
        """Get Pydantic model for the submodel"""

        if _model:
            new_stack = self._stack + ((self._cls, field_name, self.meta.max_recursion),)

            # Get pydantic schema for the submodel
            prefix_len = len(field_name) + 1

            def get_fields_to_carry_on(field_tuple: Tuple[str, ...]) -> Tuple[str, ...]:
                return tuple(
                    str(v[prefix_len:]) for v in field_tuple if v.startswith(field_name + ".")
                )

            pmodel = _pydantic_recursion_protector(
                _model,
                exclude=get_fields_to_carry_on(self.meta.exclude),
                include=get_fields_to_carry_on(self.meta.include),
                computed=get_fields_to_carry_on(self.meta.computed),
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
    exclude_readonly: bool = False,
    meta_override: Optional[Type] = None,
    model_config: Optional[ConfigDict] = None,
    validators: Optional[Dict[str, Any]] = None,
    module: str = __name__,
) -> Type[PydanticModel]:
    """
    Function to build `Pydantic Model <https://docs.pydantic.dev/latest/concepts/models/>`__ off Tortoise Model.

    :param cls: The Tortoise Model
    :param name: Specify a custom name explicitly, instead of a generated name.
    :param exclude: Extra fields to exclude from the provided model.
    :param include: Extra fields to include from the provided model.
    :param computed: Extra computed fields to include from the provided model.
    :param optional: Extra optional fields for the provided model.
    :param allow_cycles: Do we allow any cycles in the generated model?
        This is only useful for recursive/self-referential models.

        A value of ``False`` (the default) will prevent any and all backtracking.
    :param sort_alphabetically: Sort the parameters alphabetically instead of Field-definition order.

        The default order would be:

            * Field definition order +
            * order of reverse relations (as discovered) +
            * order of computed functions (as provided).
    :param exclude_readonly: Build a subset model that excludes any readonly fields
    :param meta_override: A PydanticMeta class to override model's values.
    :param model_config: A custom config to use as pydantic config.
    :param validators: A dictionary of methods that validate fields.
    :param module: The name of the module that the model belongs to.

        Note: Created pydantic model uses config_class parameter and PydanticMeta's
            config_class as its Config class's bases(Only if provided!), but it
            ignores ``fields`` config. pydantic_model_creator will generate fields by
            include/exclude/computed parameters automatically.
    """
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
        module=module,
    )
    return pmc.create_pydantic_model()
