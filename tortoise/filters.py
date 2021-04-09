import operator
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Tuple

from pypika import Table
from pypika.enums import DatePart, SqlTypes
from pypika.functions import Cast, Extract, Upper
from pypika.terms import (
    BasicCriterion,
    Criterion,
    Enum,
    Equality,
    Term,
    ValueWrapper,
    date,
    format_quotes,
)

from tortoise.fields import Field
from tortoise.fields.relational import BackwardFKRelation, ManyToManyFieldInstance

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


##############################################################################
# Here we monkey-patch PyPika Valuewrapper to behave differently for MySQL
##############################################################################


def get_value_sql(self, **kwargs):  # pragma: nocoverage
    quote_char = kwargs.get("secondary_quote_char") or ""
    dialect = kwargs.get("dialect")
    if dialect:
        dialect = dialect.value

    if isinstance(self.value, Term):
        return self.value.get_sql(**kwargs)
    if isinstance(self.value, Enum):
        return self.value.value
    if isinstance(self.value, date):
        value = self.value.isoformat()
        return format_quotes(value, quote_char)
    if isinstance(self.value, str):
        value = self.value.replace(quote_char, quote_char * 2)
        if dialect == "mysql":
            value = value.replace("\\", "\\\\")
        return format_quotes(value, quote_char)
    if isinstance(self.value, bool):
        return str.lower(str(self.value))
    if self.value is None:
        return "null"
    return str(self.value)


ValueWrapper.get_value_sql = get_value_sql


##############################################################################


class Like(BasicCriterion):  # type: ignore
    def __init__(self, left, right, alias=None, escape=" ESCAPE '\\'") -> None:
        """
        A Like that supports an ESCAPE clause
        """
        super().__init__(" LIKE ", left, right, alias=alias)
        self.escape = escape

    def get_sql(self, quote_char='"', with_alias=False, **kwargs):
        sql = "{left}{comparator}{right}{escape}".format(
            comparator=self.comparator,
            left=self.left.get_sql(quote_char=quote_char, **kwargs),
            right=self.right.get_sql(quote_char=quote_char, **kwargs),
            escape=self.escape,
        )
        if with_alias and self.alias:  # pragma: nocoverage
            return '{sql} "{alias}"'.format(sql=sql, alias=self.alias)
        return sql


def escape_like(val: str) -> str:
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


##############################################################################
# Encoders
# Should be type: (Any, instance: "Model", field: Field) -> type:
##############################################################################


def list_encoder(values: Iterable[Any], instance: "Model", field: Field) -> list:
    """Encodes an iterable of a given field into a database-compatible format."""
    return [field.to_db_value(element, instance) for element in values]


def related_list_encoder(values: Iterable[Any], instance: "Model", field: Field) -> list:
    return [
        field.to_db_value(element.pk if hasattr(element, "pk") else element, instance)
        for element in values
    ]


def bool_encoder(value: Any, instance: "Model", field: Field) -> bool:
    return bool(value)


def string_encoder(value: Any, instance: "Model", field: Field) -> str:
    return str(value)


##############################################################################
# Operators
# Should be type: (field: Term, value: Any) -> Criterion:
##############################################################################


def is_in(field: Term, value: Any) -> Criterion:
    if value:
        return field.isin(value)
    # SQL has no False, so we return 1=0
    return BasicCriterion(Equality.eq, ValueWrapper(1), ValueWrapper(0))


def not_in(field: Term, value: Any) -> Criterion:
    if value:
        return field.notin(value) | field.isnull()
    # SQL has no True, so we return 1=1
    return BasicCriterion(Equality.eq, ValueWrapper(1), ValueWrapper(1))


def between_and(field: Term, value: Tuple[Any, Any]) -> Criterion:
    return field.between(value[0], value[1])


def not_equal(field: Term, value: Any) -> Criterion:
    return field.ne(value) | field.isnull()


def is_null(field: Term, value: Any) -> Criterion:
    if value:
        return field.isnull()
    return field.notnull()


def not_null(field: Term, value: Any) -> Criterion:
    if value:
        return field.notnull()
    return field.isnull()


def contains(field: Term, value: str) -> Criterion:
    return Like(Cast(field, SqlTypes.VARCHAR), field.wrap_constant(f"%{escape_like(value)}%"))


def search(field: Term, value: str):
    # will be override in each executor
    pass


def starts_with(field: Term, value: str) -> Criterion:
    return Like(Cast(field, SqlTypes.VARCHAR), field.wrap_constant(f"{escape_like(value)}%"))


def ends_with(field: Term, value: str) -> Criterion:
    return Like(Cast(field, SqlTypes.VARCHAR), field.wrap_constant(f"%{escape_like(value)}"))


def insensitive_exact(field: Term, value: str) -> Criterion:
    return Upper(Cast(field, SqlTypes.VARCHAR)).eq(Upper(str(value)))


def insensitive_contains(field: Term, value: str) -> Criterion:
    return Like(
        Upper(Cast(field, SqlTypes.VARCHAR)), field.wrap_constant(Upper(f"%{escape_like(value)}%"))
    )


def insensitive_starts_with(field: Term, value: str) -> Criterion:
    return Like(
        Upper(Cast(field, SqlTypes.VARCHAR)), field.wrap_constant(Upper(f"{escape_like(value)}%"))
    )


def insensitive_ends_with(field: Term, value: str) -> Criterion:
    return Like(
        Upper(Cast(field, SqlTypes.VARCHAR)), field.wrap_constant(Upper(f"%{escape_like(value)}"))
    )


def extract_year_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.year, field).eq(value)


def extract_quarter_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.quarter, field).eq(value)


def extract_month_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.month, field).eq(value)


def extract_week_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.week, field).eq(value)


def extract_day_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.day, field).eq(value)


def extract_hour_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.hour, field).eq(value)


def extract_minute_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.minute, field).eq(value)


def extract_second_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.second, field).eq(value)


def extract_microsecond_equal(field: Term, value: int) -> Criterion:
    return Extract(DatePart.microsecond, field).eq(value)


##############################################################################
# Filter resolvers
##############################################################################


def get_m2m_filters(field_name: str, field: ManyToManyFieldInstance) -> Dict[str, dict]:
    target_table_pk = field.related_model._meta.pk
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


def get_backward_fk_filters(field_name: str, field: BackwardFKRelation) -> Dict[str, dict]:
    target_table_pk = field.related_model._meta.pk
    return {
        field_name: {
            "field": field.related_model._meta.pk_attr,
            "backward_key": field.relation_field,
            "operator": operator.eq,
            "table": Table(field.related_model._meta.db_table),
            "value_encoder": target_table_pk.to_db_value,
        },
        f"{field_name}__not": {
            "field": field.related_model._meta.pk_attr,
            "backward_key": field.relation_field,
            "operator": not_equal,
            "table": Table(field.related_model._meta.db_table),
            "value_encoder": target_table_pk.to_db_value,
        },
        f"{field_name}__in": {
            "field": field.related_model._meta.pk_attr,
            "backward_key": field.relation_field,
            "operator": is_in,
            "table": Table(field.related_model._meta.db_table),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
        f"{field_name}__not_in": {
            "field": field.related_model._meta.pk_attr,
            "backward_key": field.relation_field,
            "operator": not_in,
            "table": Table(field.related_model._meta.db_table),
            "value_encoder": partial(related_list_encoder, field=target_table_pk),
        },
        f"{field_name}__isnull": {
            "field": field.related_model._meta.pk_attr,
            "backward_key": field.relation_field,
            "operator": is_null,
            "table": Table(field.related_model._meta.db_table),
        },
        f"{field_name}__not_isnull": {
            "field": field.related_model._meta.pk_attr,
            "backward_key": field.relation_field,
            "operator": not_null,
            "table": Table(field.related_model._meta.db_table),
        },
    }


def get_filters_for_field(
    field_name: str, field: Optional[Field], source_field: str
) -> Dict[str, dict]:
    if isinstance(field, ManyToManyFieldInstance):
        return get_m2m_filters(field_name, field)
    if isinstance(field, BackwardFKRelation):
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
        f"{field_name}__range": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": between_and,
            "value_encoder": list_encoder,
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
        f"{field_name}__search": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": search,
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
        f"{field_name}__year": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_year_equal,
        },
        f"{field_name}__quarter": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_quarter_equal,
        },
        f"{field_name}__month": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_month_equal,
        },
        f"{field_name}__week": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_week_equal,
        },
        f"{field_name}__day": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_day_equal,
        },
        f"{field_name}__hour": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_hour_equal,
        },
        f"{field_name}__minute": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_minute_equal,
        },
        f"{field_name}__second": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_second_equal,
        },
        f"{field_name}__microsecond": {
            "field": actual_field_name,
            "source_field": source_field,
            "operator": extract_microsecond_equal,
        },
    }
