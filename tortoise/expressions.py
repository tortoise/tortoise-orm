import operator
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from pypika import Case as PypikaCase
from pypika import Field as PypikaField
from pypika import Table
from pypika.functions import DistinctOptionFunction
from pypika.terms import ArithmeticExpression, Criterion
from pypika.terms import Function as PypikaFunction
from pypika.terms import Term
from pypika.utils import format_alias_sql

from tortoise.exceptions import ConfigurationError, FieldError, OperationalError
from tortoise.fields.relational import (
    BackwardFKRelation,
    ForeignKeyFieldInstance,
    RelationalField,
)
from tortoise.filters import FilterInfoDict
from tortoise.query_utils import QueryModifier, _get_joins_for_related_field

if TYPE_CHECKING:  # pragma: nocoverage
    from pypika.queries import Selectable

    from tortoise.fields.base import Field
    from tortoise.models import Model
    from tortoise.queryset import AwaitableQuery


class F(PypikaField):  # type: ignore
    @classmethod
    def resolver_arithmetic_expression(
        cls,
        model: "Type[Model]",
        arithmetic_expression_or_field: Term,
    ) -> Tuple[Term, Optional[PypikaField]]:
        field_object = None

        if isinstance(arithmetic_expression_or_field, PypikaField):
            name = arithmetic_expression_or_field.name
            try:
                arithmetic_expression_or_field.name = model._meta.fields_db_projection[name]

                field_object = model._meta.fields_map.get(name, None)
                if field_object:
                    func = field_object.get_for_dialect(
                        model._meta.db.capabilities.dialect, "function_cast"
                    )
                    if func:
                        arithmetic_expression_or_field = func(
                            field_object, arithmetic_expression_or_field
                        )
            except KeyError:
                raise FieldError(f"There is no non-virtual field {name} on Model {model.__name__}")
        elif isinstance(arithmetic_expression_or_field, ArithmeticExpression):
            left = arithmetic_expression_or_field.left
            right = arithmetic_expression_or_field.right
            (
                arithmetic_expression_or_field.left,
                left_field_object,
            ) = cls.resolver_arithmetic_expression(model, left)
            if left_field_object:
                if field_object and type(field_object) != type(left_field_object):
                    raise FieldError(
                        "Cannot use arithmetic expression between different field type"
                    )
                field_object = left_field_object

            (
                arithmetic_expression_or_field.right,
                right_field_object,
            ) = cls.resolver_arithmetic_expression(model, right)
            if right_field_object:
                if field_object and type(field_object) != type(right_field_object):
                    raise FieldError(
                        "Cannot use arithmetic expression between different field type"
                    )
                field_object = right_field_object

        return arithmetic_expression_or_field, field_object


class Subquery(Term):  # type: ignore
    def __init__(self, query: "AwaitableQuery"):
        super().__init__()
        self.query = query

    def get_sql(self, **kwargs: Any) -> str:
        return self.query.as_query().get_sql(**kwargs)

    def as_(self, alias: str) -> "Selectable":
        return self.query.as_query().as_(alias)


class RawSQL(Term):  # type: ignore
    def __init__(self, sql: str):
        super().__init__()
        self.sql = sql

    def get_sql(self, with_alias: bool = False, **kwargs: Any) -> str:
        if with_alias:
            return format_alias_sql(sql=self.sql, alias=self.alias, **kwargs)
        return self.sql


class Expression:
    """
    Parent class for expressions
    """

    def resolve(self, model: "Type[Model]", table: Table) -> Any:
        raise NotImplementedError()


class Q(Expression):
    """
    Q Expression container.
    Q Expressions are a useful tool to compose a query from many small parts.

    :param join_type: Is the join an AND or OR join type?
    :param args: Inner ``Q`` expressions that you want to wrap.
    :param kwargs: Filter statements that this Q object should encapsulate.
    """

    __slots__ = (
        "children",
        "filters",
        "join_type",
        "_is_negated",
        "_annotations",
        "_custom_filters",
    )

    AND = "AND"
    OR = "OR"

    def __init__(self, *args: "Q", join_type: str = AND, **kwargs: Any) -> None:
        if args and kwargs:
            newarg = Q(join_type=join_type, **kwargs)
            args = (newarg,) + args
            kwargs = {}
        if not all(isinstance(node, Q) for node in args):
            raise OperationalError("All ordered arguments must be Q nodes")
        #: Contains the sub-Q's that this Q is made up of
        self.children: Tuple[Q, ...] = args
        #: Contains the filters applied to this Q
        self.filters: Dict[str, FilterInfoDict] = kwargs
        if join_type not in {self.AND, self.OR}:
            raise OperationalError("join_type must be AND or OR")
        #: Specifies if this Q does an AND or OR on its children
        self.join_type = join_type
        self._is_negated = False
        self._annotations: Dict[str, Any] = {}
        self._custom_filters: Dict[str, FilterInfoDict] = {}

    def __and__(self, other: "Q") -> "Q":
        """
        Returns a binary AND of Q objects, use ``AND`` operator.

        :raises OperationalError: AND operation requires a Q node
        """
        if not isinstance(other, Q):
            raise OperationalError("AND operation requires a Q node")
        return Q(self, other, join_type=self.AND)

    def __or__(self, other: "Q") -> "Q":
        """
        Returns a binary OR of Q objects, use ``OR`` operator.

        :raises OperationalError: OR operation requires a Q node
        """
        if not isinstance(other, Q):
            raise OperationalError("OR operation requires a Q node")
        return Q(self, other, join_type=self.OR)

    def __invert__(self) -> "Q":
        """
        Returns a negated instance of the Q object, use ``~`` operator.
        """
        q = Q(*self.children, join_type=self.join_type, **self.filters)
        q.negate()
        return q

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Q):
            return False
        return (
            self.children == other.children
            and self.join_type == other.join_type
            and self.filters == other.filters
        )

    def negate(self) -> None:
        """
        Negates the current Q object. (mutation)
        """
        self._is_negated = not self._is_negated

    def _resolve_nested_filter(
        self, model: "Type[Model]", key: str, value: Any, table: Table
    ) -> QueryModifier:
        related_field_name, __, forwarded_fields = key.partition("__")
        related_field = cast(RelationalField, model._meta.fields_map[related_field_name])
        required_joins = _get_joins_for_related_field(table, related_field, related_field_name)
        q = Q(**{forwarded_fields: value})
        q._annotations = self._annotations
        q._custom_filters = self._custom_filters
        modifier = q.resolve(
            model=related_field.related_model,
            table=required_joins[-1][0],
        )
        return QueryModifier(joins=required_joins) & modifier

    def _resolve_custom_kwarg(
        self, model: "Type[Model]", key: str, value: Any, table: Table
    ) -> QueryModifier:
        having_info = self._custom_filters[key]
        annotation = self._annotations[having_info["field"]]
        if isinstance(annotation, Term):
            annotation_info = {"field": annotation}
        else:
            annotation_info = annotation.resolve(model, table)

        operator = having_info["operator"]
        overridden_operator = model._meta.db.executor_class.get_overridden_filter_func(
            filter_func=operator
        )
        if overridden_operator:
            operator = overridden_operator
        if annotation_info["field"].is_aggregate:
            modifier = QueryModifier(having_criterion=operator(annotation_info["field"], value))
        else:
            modifier = QueryModifier(where_criterion=operator(annotation_info["field"], value))
        return modifier

    def _process_filter_kwarg(
        self, model: "Type[Model]", key: str, value: Any, table: Table
    ) -> Tuple[Criterion, Optional[Tuple[Table, Criterion]]]:
        join = None

        if value is None and f"{key}__isnull" in model._meta.filters:
            param = model._meta.get_filter(f"{key}__isnull")
            value = True
        else:
            param = model._meta.get_filter(key)

        pk_db_field = model._meta.db_pk_column
        if param.get("table"):
            join = (
                param["table"],
                table[pk_db_field] == param["table"][param["backward_key"]],
            )
            if param.get("value_encoder"):
                value = param["value_encoder"](value, model)
            criterion = param["operator"](param["table"][param["field"]], value)
        else:
            if isinstance(value, Term):
                encoded_value = value
            else:
                field_object = model._meta.fields_map[param["field"]]
                encoded_value = (
                    param["value_encoder"](value, model, field_object)
                    if param.get("value_encoder")
                    else model._meta.db.executor_class._field_to_db(field_object, value, model)
                )
            op = param["operator"]
            # this is an ugly hack
            if op == operator.eq:
                encoded_value = model._meta.db.query_class._builder()._wrapper_cls(encoded_value)
            criterion = op(table[param["source_field"]], encoded_value)
        return criterion, join

    def _resolve_regular_kwarg(
        self, model: "Type[Model]", key: str, value: Any, table: Table
    ) -> QueryModifier:
        if key not in model._meta.filters and key.split("__")[0] in model._meta.fetch_fields:
            modifier = self._resolve_nested_filter(model, key, value, table)
        else:
            criterion, join = self._process_filter_kwarg(model, key, value, table)
            joins = [join] if join else []
            modifier = QueryModifier(where_criterion=criterion, joins=joins)
        return modifier

    def _get_actual_filter_params(
        self, model: "Type[Model]", key: str, value: Table
    ) -> Tuple[str, Any]:
        filter_key = key
        if key in model._meta.fk_fields or key in model._meta.o2o_fields:
            field_object = model._meta.fields_map[key]
            if hasattr(value, "pk"):
                filter_value = value.pk
            else:
                filter_value = value
            filter_key = cast(str, field_object.source_field)
        elif key in model._meta.m2m_fields:
            if hasattr(value, "pk"):
                filter_value = value.pk
            else:
                filter_value = value
        elif (
            key.split("__")[0] in model._meta.fetch_fields
            or key in self._custom_filters
            or key in model._meta.filters
        ):
            filter_value = value
        else:
            allowed = sorted(
                model._meta.fields | model._meta.fetch_fields | set(self._custom_filters)
            )
            raise FieldError(f"Unknown filter param '{key}'. Allowed base values are {allowed}")
        return filter_key, filter_value

    def _resolve_kwargs(self, model: "Type[Model]", table: Table) -> QueryModifier:
        modifier = QueryModifier()
        for raw_key, raw_value in self.filters.items():
            key, value = self._get_actual_filter_params(model, raw_key, raw_value)
            if key in self._custom_filters:
                filter_modifier = self._resolve_custom_kwarg(model, key, value, table)
            else:
                filter_modifier = self._resolve_regular_kwarg(model, key, value, table)

            if self.join_type == self.AND:
                modifier &= filter_modifier
            else:
                modifier |= filter_modifier
        if self._is_negated:
            modifier = ~modifier
        return modifier

    def _resolve_children(self, model: "Type[Model]", table: Table) -> QueryModifier:
        modifier = QueryModifier()
        for node in self.children:
            node._annotations = self._annotations
            node._custom_filters = self._custom_filters
            node_modifier = node.resolve(model, table)
            if self.join_type == self.AND:
                modifier &= node_modifier
            else:
                modifier |= node_modifier

        if self._is_negated:
            modifier = ~modifier
        return modifier

    def resolve(
        self,
        model: "Type[Model]",
        table: Table,
    ) -> QueryModifier:
        """
        Resolves the logical Q chain into the parts of a SQL statement.

        :param model: The Model this Q Expression should be resolved on.
        :param table: ``pypika.Table`` to keep track of the virtual SQL table
            (to allow self referential joins)
        """
        if self.filters:
            return self._resolve_kwargs(model, table)
        return self._resolve_children(model, table)


class Function(Expression):
    """
    Function/Aggregate base.

    :param field: Field name
    :param default_values: Extra parameters to the function.

    .. attribute:: database_func
        :annotation: pypika.terms.Function

        The pypika function this represents.

    .. attribute:: populate_field_object
        :annotation: bool = False

        Enable populate_field_object where we want to try and preserve the field type.
    """

    __slots__ = ("field", "field_object", "default_values")

    database_func = PypikaFunction
    # Enable populate_field_object where we want to try and preserve the field type.
    populate_field_object = False

    def __init__(
        self, field: Union[str, F, ArithmeticExpression, "Function"], *default_values: Any
    ) -> None:
        self.field = field
        self.field_object: "Optional[Field]" = None
        self.default_values = default_values

    def _get_function_field(
        self, field: Union[ArithmeticExpression, PypikaField, str], *default_values
    ):
        return self.database_func(field, *default_values)

    def _resolve_field_for_model(self, model: "Type[Model]", table: Table, field: str) -> dict:
        joins = []
        fields = field.split("__")

        for iter_field in fields[:-1]:
            if iter_field not in model._meta.fetch_fields:
                raise ConfigurationError(f"{field} not resolvable")

            related_field = cast(RelationalField, model._meta.fields_map[iter_field])
            joins.append((table, iter_field, related_field))

            model = related_field.related_model
            related_table: Table = related_field.related_model._meta.basetable
            if isinstance(related_field, ForeignKeyFieldInstance):
                # Only FK's can be to same table, so we only auto-alias FK join tables
                related_table = related_table.as_(f"{table.get_table_name()}__{iter_field}")
            table = related_table

        last_field = fields[-1]
        if last_field in model._meta.fetch_fields:
            related_field = cast(RelationalField, model._meta.fields_map[last_field])
            related_field_meta = related_field.related_model._meta
            joins.append((table, last_field, related_field))
            related_table = related_field_meta.basetable

            if isinstance(related_field, BackwardFKRelation):
                if table == related_table:
                    related_table = related_table.as_(f"{table.get_table_name()}__{last_field}")

            field = related_table[related_field_meta.db_pk_column]
        else:
            field_object = model._meta.fields_map[last_field]
            if field_object.source_field:
                field = table[field_object.source_field]
            else:
                field = table[last_field]
            if self.populate_field_object:
                self.field_object = model._meta.fields_map.get(last_field, None)
                if self.field_object:  # pragma: nobranch
                    func = self.field_object.get_for_dialect(
                        model._meta.db.capabilities.dialect, "function_cast"
                    )
                    if func:
                        field = func(self.field_object, field)

        return {"joins": joins, "field": field}

    def _resolve_default_values(self, model: "Type[Model]", table: Table) -> Iterator[Any]:
        for default_value in self.default_values:
            if isinstance(default_value, Function):
                yield default_value.resolve(model, table)["field"]
            else:
                yield default_value

    def resolve(self, model: "Type[Model]", table: Table) -> dict:
        """
        Used to resolve the Function statement for SQL generation.

        :param model: Model the function is applied on to.
        :param table: ``pypika.Table`` to keep track of the virtual SQL table
            (to allow self referential joins)
        :return: Dict with keys ``"joins"`` and ``"fields"``
        """

        default_values = self._resolve_default_values(model, table)

        if isinstance(self.field, str):
            function = self._resolve_field_for_model(model, table, self.field)
            function["field"] = self._get_function_field(function["field"], *default_values)
            return function
        elif isinstance(self.field, Function):
            function = self.field.resolve(model, table)
            function["field"] = self._get_function_field(function["field"], *default_values)
            return function

        field, field_object = F.resolver_arithmetic_expression(model, self.field)
        if self.populate_field_object:
            self.field_object = field_object
        return {"joins": [], "field": self._get_function_field(field, *default_values)}


class Aggregate(Function):
    """
    Base for SQL Aggregates.

    :param field: Field name
    :param default_values: Extra parameters to the function.
    :param is_distinct: Flag for aggregate with distinction
    """

    database_func = DistinctOptionFunction

    def __init__(
        self,
        field: Union[str, F, ArithmeticExpression],
        *default_values: Any,
        distinct: bool = False,
        _filter: Optional[Q] = None,
    ) -> None:
        super().__init__(field, *default_values)
        self.distinct = distinct
        self.filter = _filter

    def _get_function_field(
        self, field: Union[ArithmeticExpression, PypikaField, str], *default_values
    ):
        if self.distinct:
            return self.database_func(field, *default_values).distinct()
        return self.database_func(field, *default_values)

    def _resolve_field_for_model(self, model: "Type[Model]", table: Table, field: str) -> dict:
        ret = super()._resolve_field_for_model(model, table, field)
        if self.filter:
            modifier = QueryModifier()
            modifier &= self.filter.resolve(model, model._meta.basetable)
            where_criterion, joins, having_criterion = modifier.get_query_modifiers()
            ret["field"] = PypikaCase().when(where_criterion, ret["field"]).else_(None)

        return ret


class When(Expression):
    """
    When expression.

    :param args: Q objects
    :param kwargs: keyword criterion like filter
    :param then: value for criterion
    :param negate: false (default)
    """

    def __init__(
        self,
        *args: Q,
        then: Union[str, F, ArithmeticExpression, Function],
        negate: bool = False,
        **kwargs: Any,
    ) -> None:
        self.args = args
        self.then = then
        self.negate = negate
        self.kwargs = kwargs

    def _resolve_q_objects(self) -> List[Q]:
        q_objects = []
        for arg in self.args:
            if not isinstance(arg, Q):
                raise TypeError("expected Q objects as args")
            if self.negate:
                q_objects.append(~arg)
            else:
                q_objects.append(arg)

        for key, value in self.kwargs.items():
            if self.negate:
                q_objects.append(~Q(**{key: value}))
            else:
                q_objects.append(Q(**{key: value}))
        return q_objects

    def resolve(self, model: "Type[Model]", table: Table) -> tuple:
        q_objects = self._resolve_q_objects()

        modifier = QueryModifier()
        for node in q_objects:
            modifier &= node.resolve(model, model._meta.basetable)

        if isinstance(self.then, Function):
            then = self.then.resolve(model, table)["field"]
        elif isinstance(self.then, Term):
            then = F.resolver_arithmetic_expression(model, self.then)[0]
        else:
            then = Term.wrap_constant(self.then)

        return modifier.where_criterion, then


class Case(Expression):
    """
    Case expression.

    :param args: When objects
    :param default: value for 'CASE WHEN ... THEN ... ELSE <default> END'
    """

    def __init__(
        self, *args: When, default: Union[str, F, ArithmeticExpression, Function] = None
    ) -> None:
        self.args = args
        self.default = default

    def resolve(self, model: "Type[Model]", table: Table) -> dict:
        case = PypikaCase()
        for arg in self.args:
            if not isinstance(arg, When):
                raise TypeError("expected When objects as args")
            criterion, term = arg.resolve(model, table)
            case = case.when(criterion, term)

        if isinstance(self.default, Function):
            case = case.else_(self.default.resolve(model, table)["field"])
        elif isinstance(self.default, Term):
            case = case.else_(F.resolver_arithmetic_expression(model, self.default)[0])
        else:
            case = case.else_(Term.wrap_constant(self.default))

        return {"joins": [], "field": case}
