import dataclasses
from typing import Type, Optional, Any, TYPE_CHECKING, Dict, List

from tortoise.fields import Field
from tortoise.fields.relational import RelationalField, ForeignKeyFieldInstance, ManyToManyFieldInstance, \
    BackwardOneToOneRelation, BackwardFKRelation, OneToOneFieldInstance, MODEL

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


@dataclasses.dataclass
class FieldDescriptionBase:
    name: str
    field_type: Type[Field]
    nullable: bool
    constraints: Dict
    python_type: Optional[type] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    docstring: Optional[str] = None


@dataclasses.dataclass
class FieldDescription(FieldDescriptionBase):
    ...


@dataclasses.dataclass
class RelationalFieldDescription(FieldDescriptionBase):
    python_type: Optional[Type["Model"]] = None


@dataclasses.dataclass
class ForeignKeyFieldInstanceDescription(RelationalFieldDescription):
    raw_field: Optional[str] = ""


@dataclasses.dataclass
class BackwardFKRelationDescription(ForeignKeyFieldInstanceDescription):
    ...


@dataclasses.dataclass
class OneToOneFieldInstanceDescription(ForeignKeyFieldInstanceDescription):
    ...


@dataclasses.dataclass
class BackwardOneToOneRelationDescription(ForeignKeyFieldInstanceDescription):
    ...


@dataclasses.dataclass
class ManyToManyFieldInstanceDescription(RelationalFieldDescription):
    ...


@dataclasses.dataclass
class ModelDescription:
    pk_field: FieldDescriptionBase
    data_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    fk_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    backward_fk_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    o2o_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    backward_o2o_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    m2m_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)


def describe_model_by_dataclass(cls: Type[MODEL]) -> ModelDescription:
    return ModelDescription(
        pk_field=describe_field_by_dataclass(cls._meta.fields_map[cls._meta.pk_attr]),
        data_fields=[
            describe_field_by_dataclass(field)
            for name, field in cls._meta.fields_map.items()
            if name != cls._meta.pk_attr and name in (cls._meta.fields - cls._meta.fetch_fields)
        ],
        fk_fields=[
            describe_field_by_dataclass(field)
            for name, field in cls._meta.fields_map.items()
            if name in cls._meta.fk_fields
        ],
        backward_fk_fields=[
            describe_field_by_dataclass(field)
            for name, field in cls._meta.fields_map.items()
            if name in cls._meta.backward_fk_fields
        ],
        o2o_fields=[
            describe_field_by_dataclass(field)
            for name, field in cls._meta.fields_map.items()
            if name in cls._meta.o2o_fields
        ],
        backward_o2o_fields=[
            describe_field_by_dataclass(field)
            for name, field in cls._meta.fields_map.items()
            if name in cls._meta.backward_o2o_fields
        ],
        m2m_fields=[
            describe_field_by_dataclass(field)
            for name, field in cls._meta.fields_map.items()
            if name in cls._meta.m2m_fields
        ],
    )


def describe_field_by_dataclass(field: Field) -> FieldDescriptionBase:
    field_type = getattr(field, "related_model", field.field_type)
    if isinstance(field, RelationalField):
        if isinstance(field, ForeignKeyFieldInstance):
            # ForeignKeyFieldInstance -> RelationalField
            if isinstance(field, OneToOneFieldInstance):
                # OneToOneFieldInstance -> ForeignKeyFieldInstance -> RelationalField
                return OneToOneFieldInstanceDescription(
                    name=field.model_field_name,
                    field_type=field.__class__,
                    python_type=field_type,
                    nullable=field.null,
                    default=field.default,
                    description=field.description,
                    docstring=field.docstring,
                    constraints=field.constraints,
                    raw_field=field.source_field,
                )
            return ForeignKeyFieldInstanceDescription(
                name=field.model_field_name,
                field_type=field.__class__,
                python_type=field_type,
                nullable=field.null,
                default=field.default,
                description=field.description,
                docstring=field.docstring,
                constraints=field.constraints,
                raw_field=field.source_field,
            )
        if isinstance(field, BackwardFKRelation):
            # BackwardFKRelation -> RelationalField
            if isinstance(field, BackwardOneToOneRelation):
                # BackwardOneToOneRelation -> BackwardFKRelation -> RelationalField
                return BackwardOneToOneRelationDescription(
                    name=field.model_field_name,
                    field_type=field.__class__,
                    python_type=field_type,
                    nullable=field.null,
                    default=field.default,
                    description=field.description,
                    docstring=field.docstring,
                    constraints=field.constraints,
                    raw_field=field.source_field,
                )
            return BackwardFKRelationDescription(
                name=field.model_field_name,
                field_type=field.__class__,
                python_type=field.related_model,
                nullable=field.null,
                default=field.default,
                description=field.description,
                docstring=field.docstring,
                constraints=field.constraints,
            )
        if isinstance(field, ManyToManyFieldInstance):
            # ManyToManyFieldInstance -> RelationalField
            return ManyToManyFieldInstanceDescription(
                name=field.model_field_name,
                field_type=field.__class__,
                python_type=field.related_model,
                nullable=field.null,
                default=field.default,
                description=field.description,
                docstring=field.docstring,
                constraints=field.constraints,
            )
        return RelationalFieldDescription(
            name=field.model_field_name,
            field_type=field.__class__,
            python_type=field.related_model,
            nullable=field.null,
            default=field.default,
            description=field.description,
            docstring=field.docstring,
            constraints=field.constraints,
        )
    return FieldDescription(
        name=field.model_field_name,
        field_type=field.__class__,
        python_type=field.field_type,
        nullable=field.null,
        default=field.default,
        description=field.description,
        docstring=field.docstring,
        constraints=field.constraints,
    )
