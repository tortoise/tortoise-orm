import dataclasses
import inspect
from typing import Type, Optional, Any, TYPE_CHECKING, Dict, Tuple, List

from tortoise.fields import Field
from tortoise.fields.relational import RelationalField, ForeignKeyFieldInstance, ManyToManyFieldInstance, \
    BackwardOneToOneRelation, BackwardFKRelation, OneToOneFieldInstance, MODEL

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


@dataclasses.dataclass
class FieldDescriptionBase:
    name: str
    field_type: Type[Field]
    generated: bool
    nullable: bool
    unique: bool
    indexed: bool
    constraints: Dict
    python_type: Optional[type] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    docstring: Optional[str] = None
    db_field_types: Optional[Dict[str, str]] = None


@dataclasses.dataclass
class FieldDescription(FieldDescriptionBase):
    db_column: str = ""


@dataclasses.dataclass
class RelationalFieldDescription(FieldDescriptionBase):
    db_constraint: bool = False
    python_type: Optional[Type["Model"]] = None


@dataclasses.dataclass
class ForeignKeyFieldInstanceDescription(RelationalFieldDescription):
    raw_field: Optional[str] = ""
    on_delete: str = ""


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
    model_name: str = ""
    related_name: str = ""
    forward_key: str = ""
    backward_key: str = ""
    through: str = ""
    on_delete: str = ""
    _generated: bool = False


@dataclasses.dataclass
class ModelDescription:
    name: str
    table: str
    abstract: bool
    description: Optional[str]
    pk_field: FieldDescriptionBase
    app: Optional[str] = None
    docstring: Optional[str] = None
    unique_together: Tuple[Tuple[str, ...], ...] = dataclasses.field(default_factory=tuple)
    indexes: Tuple[Tuple[str, ...], ...] = dataclasses.field(default_factory=tuple)
    data_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    fk_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    backward_fk_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    o2o_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    backward_o2o_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)
    m2m_fields: List[FieldDescriptionBase] = dataclasses.field(default_factory=list)


def describe_model_by_dataclass(cls: Type[MODEL]) -> ModelDescription:
    return ModelDescription(
        name=cls._meta.full_name,
        app=cls._meta.app,
        table=cls._meta.db_table,
        abstract=cls._meta.abstract,
        description=cls._meta.table_description or None,
        docstring=inspect.cleandoc(cls.__doc__ or "") or None,
        unique_together=cls._meta.unique_together or (),
        indexes=cls._meta.indexes or (),
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
                    generated=field.generated,
                    nullable=field.null,
                    unique=field.unique,
                    indexed=field.index or field.unique,
                    default=field.default,
                    description=field.description,
                    docstring=field.docstring,
                    constraints=field.constraints,
                    db_field_types=field.get_db_field_types() if field.has_db_field else None,
                    db_constraint=field.db_constraint,
                    raw_field=field.source_field,
                    on_delete=str(field.on_delete),
                )
            return ForeignKeyFieldInstanceDescription(
                name=field.model_field_name,
                field_type=field.__class__,
                python_type=field_type,
                generated=field.generated,
                nullable=field.null,
                unique=field.unique,
                indexed=field.index or field.unique,
                default=field.default,
                description=field.description,
                docstring=field.docstring,
                constraints=field.constraints,
                db_field_types=field.get_db_field_types() if field.has_db_field else None,
                db_constraint=field.db_constraint,
                raw_field=field.source_field,
                on_delete=str(field.on_delete),
            )
        if isinstance(field, BackwardFKRelation):
            # BackwardFKRelation -> RelationalField
            if isinstance(field, BackwardOneToOneRelation):
                # BackwardOneToOneRelation -> BackwardFKRelation -> RelationalField
                return BackwardOneToOneRelationDescription(
                    name=field.model_field_name,
                    field_type=field.__class__,
                    python_type=field_type,
                    generated=field.generated,
                    nullable=field.null,
                    unique=field.unique,
                    indexed=field.index or field.unique,
                    default=field.default,
                    description=field.description,
                    docstring=field.docstring,
                    constraints=field.constraints,
                    db_field_types=field.get_db_field_types() if field.has_db_field else None,
                    db_constraint=field.db_constraint,
                    raw_field=field.source_field,
                )
            return BackwardFKRelationDescription(
                name=field.model_field_name,
                field_type=field.__class__,
                python_type=field.related_model,
                generated=field.generated,
                nullable=field.null,
                unique=field.unique,
                indexed=field.index or field.unique,
                default=field.default,
                description=field.description,
                docstring=field.docstring,
                constraints=field.constraints,
                db_field_types=field.get_db_field_types() if field.has_db_field else None,
                db_constraint=field.db_constraint
            )
        if isinstance(field, ManyToManyFieldInstance):
            # ManyToManyFieldInstance -> RelationalField
            return ManyToManyFieldInstanceDescription(
                name=field.model_field_name,
                field_type=field.__class__,
                python_type=field.related_model,
                generated=field.generated,
                nullable=field.null,
                unique=field.unique,
                indexed=field.index or field.unique,
                default=field.default,
                description=field.description,
                docstring=field.docstring,
                constraints=field.constraints,
                db_field_types=field.get_db_field_types() if field.has_db_field else None,
                db_constraint=field.db_constraint,
                model_name=field.model_name,
                related_name=field.related_name,
                forward_key=field.forward_key,
                backward_key=field.backward_key,
                through=field.through,
                on_delete=str(field.on_delete),
                _generated=field._generated,
            )
        return RelationalFieldDescription(
            name=field.model_field_name,
            field_type=field.__class__,
            python_type=field.related_model,
            generated=field.generated,
            nullable=field.null,
            unique=field.unique,
            indexed=field.index or field.unique,
            default=field.default,
            description=field.description,
            docstring=field.docstring,
            constraints=field.constraints,
            db_field_types=field.get_db_field_types() if field.has_db_field else None,
            db_constraint=field.db_constraint
        )
    return FieldDescription(
        name=field.model_field_name,
        field_type=field.__class__,
        db_column=field.source_field or field.model_field_name,
        python_type=field.field_type,
        generated=field.generated,
        nullable=field.null,
        unique=field.unique,
        indexed=field.index or field.unique,
        default=field.default,
        description=field.description,
        docstring=field.docstring,
        constraints=field.constraints,
        db_field_types=field.get_db_field_types() if field.has_db_field else None
    )
