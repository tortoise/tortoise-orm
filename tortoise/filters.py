import operator
from functools import partial
from typing import Dict, Iterable, Optional  # noqa

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
    else:
        return field.notnull()


def not_null(field, value):
    if value:
        return field.notnull()
    else:
        return field.isnull()


def contains(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like("%{}%".format(value))


def starts_with(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like("{}%".format(value))


def ends_with(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like("%{}".format(value))


def insensitive_contains(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper("%{}%".format(value))
    )


def insensitive_starts_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper("{}%".format(value))
    )


def insensitive_ends_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper("%{}".format(value))
    )


def get_m2m_filters(field_name: str, field: fields.ManyToManyField) -> Dict[str, dict]:
    target_table_pk = field.type._meta.pk
    return {
        field_name: {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": operator.eq,
            "table": Table(field.through),
            "value_encoder": target_table_pk.to_db_value,
        },
        "{}__not".format(field_name): {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": not_equal,
            "table": Table(field.through),
            "value_encoder": target_table_pk.to_db_value,
        },
        "{}__in".format(field_name): {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": is_in,
            "table": Table(field.through),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
        "{}__not_in".format(field_name): {
            "field": field.forward_key,
            "backward_key": field.backward_key,
            "operator": not_in,
            "table": Table(field.through),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
    }


def get_backward_fk_filters(field_name: str, field: fields.BackwardFKRelation) -> Dict[str, dict]:
    target_table_pk = field.type._meta.pk
    return {
        field_name: {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": operator.eq,
            "table": Table(field.type._meta.table),
            "value_encoder": target_table_pk.to_db_value,
        },
        "{}__not".format(field_name): {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": not_equal,
            "table": Table(field.type._meta.table),
            "value_encoder": target_table_pk.to_db_value,
        },
        "{}__in".format(field_name): {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": is_in,
            "table": Table(field.type._meta.table),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
        "{}__not_in".format(field_name): {
            "field": "id",
            "backward_key": field.relation_field,
            "operator": not_in,
            "table": Table(field.type._meta.table),
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
    return {
        field_name: {"field": source_field, "operator": operator.eq},
        "{}__not".format(field_name): {"field": source_field, "operator": not_equal},
        "{}__in".format(field_name): {
            "field": source_field,
            "operator": is_in,
            "value_encoder": list_encoder,
        },
        "{}__not_in".format(field_name): {
            "field": source_field,
            "operator": not_in,
            "value_encoder": list_encoder,
        },
        "{}__isnull".format(field_name): {
            "field": source_field,
            "operator": is_null,
            "value_encoder": bool_encoder,
        },
        "{}__not_isnull".format(field_name): {
            "field": source_field,
            "operator": not_null,
            "value_encoder": bool_encoder,
        },
        "{}__gte".format(field_name): {"field": source_field, "operator": operator.ge},
        "{}__lte".format(field_name): {"field": source_field, "operator": operator.le},
        "{}__gt".format(field_name): {"field": source_field, "operator": operator.gt},
        "{}__lt".format(field_name): {"field": source_field, "operator": operator.lt},
        "{}__contains".format(field_name): {
            "field": source_field,
            "operator": contains,
            "value_encoder": string_encoder,
        },
        "{}__startswith".format(field_name): {
            "field": source_field,
            "operator": starts_with,
            "value_encoder": string_encoder,
        },
        "{}__endswith".format(field_name): {
            "field": source_field,
            "operator": ends_with,
            "value_encoder": string_encoder,
        },
        "{}__icontains".format(field_name): {
            "field": source_field,
            "operator": insensitive_contains,
            "value_encoder": string_encoder,
        },
        "{}__istartswith".format(field_name): {
            "field": source_field,
            "operator": insensitive_starts_with,
            "value_encoder": string_encoder,
        },
        "{}__iendswith".format(field_name): {
            "field": source_field,
            "operator": insensitive_ends_with,
            "value_encoder": string_encoder,
        },
    }
