import operator
from functools import partial
from typing import Dict, Optional

from pypika import Table, functions
from pypika.enums import SqlTypes

from tortoise import fields
from tortoise.fields import Field


def list_encoder(values, instance, field: Field):
    """Encodes an iterable of a given field into a database-compatible format."""
    return [field.to_db_value(element, instance) for element in values]


def related_list_encoder(values, instance, field: Field):
    return [
        field.to_db_value(element.pk if hasattr(element, "pk") else element, instance)
        for element in values
    ]


def bool_encoder(value, *args):
    return bool(value)


def string_encoder(value, *args):
    return str(value)


def is_in(field, value):
    return field.isin(value)


def not_in(field, value):
    return field.notin(value) | field.isnull()


def not_equal(field, value):
    return field.ne(value) | field.isnull()


def is_null(field, value):
    if value:
        return field.isnull()
    return field.notnull()


def not_null(field, value):
    if value:
        return field.notnull()
    return field.isnull()


def contains(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like(f"%{value}%")


def starts_with(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like(f"{value}%")


def ends_with(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like(f"%{value}")


def insensitive_exact(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).eq(functions.Upper(f"{value}"))


def insensitive_contains(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper(f"%{value}%")
    )


def insensitive_starts_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper(f"{value}%")
    )


def insensitive_ends_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper(f"%{value}")
    )


def get_m2m_filters(field_name: str, field: fields.ManyToManyField) -> Dict[str, dict]:
    target_table_pk = field.field_type._meta.pk
    return {
        field_name: {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": operator.eq,
            "table": Table(field.through),
            "value_encoder": target_table_pk.to_db_value,
        },
        f"{field_name}__not": {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": not_equal,
            "table": Table(field.through),
            "value_encoder": target_table_pk.to_db_value,
        },
        f"{field_name}__in": {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": is_in,
            "table": Table(field.through),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
        f"{field_name}__not_in": {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": not_in,
            "table": Table(field.through),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
    }


def get_backward_fk_filters(field_name: str, field: fields.BackwardFKRelation) -> Dict[str, dict]:
    target_table_pk = field.field_type._meta.pk
    return {
        field_name: {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": operator.eq,
            "table": Table(field.field_type._meta.table),
            "value_encoder": target_table_pk.to_db_value,
        },
        f"{field_name}__not": {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": not_equal,
            "table": Table(field.field_type._meta.table),
            "value_encoder": target_table_pk.to_db_value,
        },
        f"{field_name}__in": {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": is_in,
            "table": Table(field.field_type._meta.table),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
        f"{field_name}__not_in": {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": not_in,
            "table": Table(field.field_type._meta.table),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
    }


def get_filters_for_field(
    field_name: str, field: Optional[fields.Field], source_field: str
) -> Dict[str, dict]:
    if isinstance(field, fields.ManyToManyField):
        return get_m2m_filters(field_name, field)
    if isinstance(field, fields.BackwardFKRelation):
        return get_backward_fk_filters(field_name, field)
    actual_field_name = field_name
    if field_name == "pk" and field:
        actual_field_name = field.model_field_name
    return {
        field_name: {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": operator.eq,
        },
        f"{field_name}__not": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": not_equal,
        },
        f"{field_name}__in": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": is_in,
            "value_encoder": list_encoder,
        },
        f"{field_name}__not_in": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": not_in,
            "value_encoder": list_encoder,
        },
        f"{field_name}__isnull": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": is_null,
            "value_encoder": bool_encoder,
        },
        f"{field_name}__not_isnull": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": not_null,
            "value_encoder": bool_encoder,
        },
        f"{field_name}__gte": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": operator.ge,
        },
        f"{field_name}__lte": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": operator.le,
        },
        f"{field_name}__gt": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": operator.gt,
        },
        f"{field_name}__lt": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": operator.lt,
        },
        f"{field_name}__contains": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": contains,
            "value_encoder": string_encoder,
        },
        f"{field_name}__startswith": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": starts_with,
            "value_encoder": string_encoder,
        },
        f"{field_name}__endswith": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": ends_with,
            "value_encoder": string_encoder,
        },
        f"{field_name}__iexact": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": insensitive_exact,
            "value_encoder": string_encoder,
        },
        f"{field_name}__icontains": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": insensitive_contains,
            "value_encoder": string_encoder,
        },
        f"{field_name}__istartswith": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": insensitive_starts_with,
            "value_encoder": string_encoder,
        },
        f"{field_name}__iendswith": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": insensitive_ends_with,
            "value_encoder": string_encoder,
        },
    }
