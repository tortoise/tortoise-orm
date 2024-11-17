import dataclasses
import sys
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple, Type

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import ConfigDict

from tortoise.fields import Field

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


@dataclasses.dataclass
class ModelDescription:
    pk_field: Field
    data_fields: List[Field] = dataclasses.field(default_factory=list)
    fk_fields: List[Field] = dataclasses.field(default_factory=list)
    backward_fk_fields: List[Field] = dataclasses.field(default_factory=list)
    o2o_fields: List[Field] = dataclasses.field(default_factory=list)
    backward_o2o_fields: List[Field] = dataclasses.field(default_factory=list)
    m2m_fields: List[Field] = dataclasses.field(default_factory=list)

    @classmethod
    def from_model(cls, model: Type["Model"]) -> Self:
        return cls(
            pk_field=model._meta.fields_map[model._meta.pk_attr],
            data_fields=[
                field
                for name, field in model._meta.fields_map.items()
                if name != model._meta.pk_attr
                and name in (model._meta.fields - model._meta.fetch_fields)
            ],
            fk_fields=[
                field
                for name, field in model._meta.fields_map.items()
                if name in model._meta.fk_fields
            ],
            backward_fk_fields=[
                field
                for name, field in model._meta.fields_map.items()
                if name in model._meta.backward_fk_fields
            ],
            o2o_fields=[
                field
                for name, field in model._meta.fields_map.items()
                if name in model._meta.o2o_fields
            ],
            backward_o2o_fields=[
                field
                for name, field in model._meta.fields_map.items()
                if name in model._meta.backward_o2o_fields
            ],
            m2m_fields=[
                field
                for name, field in model._meta.fields_map.items()
                if name in model._meta.m2m_fields
            ],
        )


@dataclasses.dataclass
class ComputedFieldDescription:
    field_type: Any
    function: Callable[[], Any]
    description: Optional[str]


@dataclasses.dataclass
class PydanticMetaData:
    #: If not empty, only fields this property contains will be in the pydantic model
    include: Tuple[str, ...] = ()

    #: Fields listed in this property will be excluded from pydantic model
    exclude: Tuple[str, ...] = dataclasses.field(default_factory=lambda: ("Meta",))

    #: Computed fields can be listed here to use in pydantic model
    computed: Tuple[str, ...] = dataclasses.field(default_factory=tuple)

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
    def from_pydantic_meta(cls, old_pydantic_meta: Any) -> Self:
        default_meta = cls()

        def get_param_from_pydantic_meta(attr: str, default: Any) -> Any:
            return getattr(old_pydantic_meta, attr, default)

        include = tuple(get_param_from_pydantic_meta("include", default_meta.include))
        exclude = tuple(get_param_from_pydantic_meta("exclude", default_meta.exclude))
        computed = tuple(get_param_from_pydantic_meta("computed", default_meta.computed))
        backward_relations = bool(
            get_param_from_pydantic_meta("backward_relations_raw", default_meta.backward_relations)
        )
        max_recursion = int(
            get_param_from_pydantic_meta("max_recursion", default_meta.max_recursion)
        )
        allow_cycles = bool(get_param_from_pydantic_meta("allow_cycles", default_meta.allow_cycles))
        exclude_raw_fields = bool(
            get_param_from_pydantic_meta("exclude_raw_fields", default_meta.exclude_raw_fields)
        )
        sort_alphabetically = bool(
            get_param_from_pydantic_meta("sort_alphabetically", default_meta.sort_alphabetically)
        )
        model_config = get_param_from_pydantic_meta("model_config", default_meta.model_config)
        pmd = cls(
            include=include,
            exclude=exclude,
            computed=computed,
            backward_relations=backward_relations,
            max_recursion=max_recursion,
            allow_cycles=allow_cycles,
            exclude_raw_fields=exclude_raw_fields,
            sort_alphabetically=sort_alphabetically,
            model_config=model_config,
        )
        return pmd

    def construct_pydantic_meta(self, meta_override: Type) -> "PydanticMetaData":
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

        pmd = PydanticMetaData(
            include=default_include,
            exclude=default_exclude,
            computed=default_computed,
            model_config=default_config,
            backward_relations=backward_relations,
            max_recursion=max_recursion,
            exclude_raw_fields=exclude_raw_fields,
            sort_alphabetically=sort_alphabetically,
            allow_cycles=allow_cycles,
        )
        return pmd

    def finalize_meta(
        self,
        exclude: Tuple[str, ...] = (),
        include: Tuple[str, ...] = (),
        computed: Tuple[str, ...] = (),
        allow_cycles: Optional[bool] = None,
        sort_alphabetically: Optional[bool] = None,
        model_config: Optional[ConfigDict] = None,
    ) -> "PydanticMetaData":
        _sort_fields: bool = (
            self.sort_alphabetically if sort_alphabetically is None else sort_alphabetically
        )
        _allow_cycles: bool = self.allow_cycles if allow_cycles is None else allow_cycles

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
            model_config=_model_config,
        )
