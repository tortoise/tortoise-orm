from __future__ import annotations

from collections.abc import Iterable, Sequence
from itertools import chain

from pypika_tortoise.enums import Comparator
from pypika_tortoise.terms import BasicCriterion, Term, ValueWrapper
from pypika_tortoise.terms import Function as PypikaFunction

from tortoise.contrib.postgres.fields import TSVectorField
from tortoise.contrib.postgres.functions import PlainToTsQuery, ToTsVector
from tortoise.expressions import Expression, F, ResolveContext, ResolveResult, Value
from tortoise.fields import FloatField, TextField
from tortoise.query_utils import TableCriterionTuple

ScalarValue = str | int | float | bool
VectorInput = Expression | Term | str
QueryInput = Expression | Term | str
ConfigInput = Expression | Term | str
WeightInput = Expression | Term | str
RankWeightInput = Expression | Term | Sequence[float] | Sequence[int] | str
NormalizationInput = Expression | Term | int
HeadlineExpressionInput = Expression | Term | str
HeadlineOptionValue = str | int | bool


class Comp(Comparator):
    search = " @@ "


class SearchCriterion(BasicCriterion):
    def __init__(self, field: Term, expr: Term | str, vectorize: bool = True) -> None:
        vector = ToTsVector(field) if vectorize else field
        query = expr if isinstance(expr, Term) else PlainToTsQuery(ValueWrapper(expr))
        super().__init__(Comp.search, vector, query)


class _TsInfixOperator(Term):
    def __init__(self, left: Term, operator: str, right: Term) -> None:
        super().__init__()
        self.left = left
        self.operator = operator
        self.right = right

    @property
    def is_aggregate(self) -> bool | None:  # type:ignore[override]
        return self.left.is_aggregate or self.right.is_aggregate

    def get_sql(self, ctx) -> str:
        left_sql = self.left.get_sql(ctx)
        right_sql = self.right.get_sql(ctx)
        sql = f"({left_sql}{self.operator}{right_sql})"
        if ctx.with_alias and self.alias:  # pragma: nocoverage
            return f'{sql} "{self.alias}"'
        return sql


class _TsQueryInvert(Term):
    def __init__(self, term: Term) -> None:
        super().__init__()
        self.term = term

    @property
    def is_aggregate(self) -> bool | None:  # type:ignore[override]
        return self.term.is_aggregate

    def get_sql(self, ctx) -> str:
        sql = f"!!({self.term.get_sql(ctx)})"
        if ctx.with_alias and self.alias:  # pragma: nocoverage
            return f'{sql} "{self.alias}"'
        return sql


def _merge_joins(*joins: Iterable[TableCriterionTuple]) -> list[TableCriterionTuple]:
    return list(set(chain.from_iterable(joins)))


def _resolve_expression(
    value: Expression | Term | ScalarValue | Sequence[float] | Sequence[int] | str | None,
    resolve_context: ResolveContext,
    *,
    treat_str_as_field: bool,
) -> ResolveResult:
    if isinstance(value, Expression):
        return value.resolve(resolve_context)
    if isinstance(value, Term):
        return ResolveResult(term=value)
    if isinstance(value, str) and treat_str_as_field:
        return F(value).resolve(resolve_context)
    return Value(value).resolve(resolve_context)


class SearchVectorCombinable(Expression):
    def _combine(self, other: SearchVectorCombinable, reversed: bool) -> CombinedSearchVector:
        if not isinstance(other, SearchVectorCombinable):
            raise TypeError(
                "SearchVector can only be combined with other SearchVector instances, "
                f"got {other.__class__.__name__}."
            )
        if reversed:
            return CombinedSearchVector(other, self)
        return CombinedSearchVector(self, other)

    def __add__(self, other: SearchVectorCombinable) -> CombinedSearchVector:
        return self._combine(other, False)

    def __radd__(self, other: SearchVectorCombinable) -> CombinedSearchVector:
        return self._combine(other, True)


class SearchVector(SearchVectorCombinable, Expression):
    def __init__(
        self,
        *expressions: VectorInput,
        config: ConfigInput | None = None,
        weight: WeightInput | None = None,
    ):
        if not expressions:
            raise ValueError("SearchVector requires at least one expression.")
        self.expressions = expressions
        self.config = config
        self.weight = weight

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        resolved = [
            _resolve_expression(expr, resolve_context, treat_str_as_field=True)
            for expr in self.expressions
        ]
        terms = [item.term for item in resolved]
        joins = _merge_joins(*(item.joins for item in resolved))

        combined = terms[0]
        for term in terms[1:]:
            combined = _TsInfixOperator(combined, " || ", ValueWrapper(" "))
            combined = _TsInfixOperator(combined, " || ", term)

        args = [combined]
        if self.config is not None:
            config_resolved = _resolve_expression(
                self.config, resolve_context, treat_str_as_field=False
            )
            args = [config_resolved.term, combined]
            joins = _merge_joins(joins, config_resolved.joins)

        vector_term = PypikaFunction("TO_TSVECTOR", *args)

        if self.weight is not None:
            weight_resolved = _resolve_expression(
                self.weight, resolve_context, treat_str_as_field=False
            )
            vector_term = PypikaFunction(
                "SETWEIGHT",
                vector_term,
                weight_resolved.term,
            )
            joins = _merge_joins(joins, weight_resolved.joins)

        return ResolveResult(term=vector_term, joins=joins, output_field=TSVectorField())


class CombinedSearchVector(SearchVectorCombinable, Expression):
    def __init__(self, left: SearchVectorCombinable, right: SearchVectorCombinable) -> None:
        self.left = left
        self.right = right

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        left = self.left.resolve(resolve_context)
        right = self.right.resolve(resolve_context)
        term = _TsInfixOperator(left.term, " || ", right.term)
        return ResolveResult(
            term=term,
            joins=_merge_joins(left.joins, right.joins),
            output_field=TSVectorField(),
        )


class SearchQueryCombinable(Expression):
    def _combine(
        self, other: SearchQueryCombinable, operator: str, reversed: bool
    ) -> CombinedSearchQuery:
        if not isinstance(other, SearchQueryCombinable):
            raise TypeError(
                "SearchQuery can only be combined with other SearchQuery instances, "
                f"got {other.__class__.__name__}."
            )
        if reversed:
            return CombinedSearchQuery(other, operator, self)
        return CombinedSearchQuery(self, operator, other)

    def __or__(self, other: SearchQueryCombinable) -> CombinedSearchQuery:
        return self._combine(other, " || ", False)

    def __ror__(self, other: SearchQueryCombinable) -> CombinedSearchQuery:
        return self._combine(other, " || ", True)

    def __and__(self, other: SearchQueryCombinable) -> CombinedSearchQuery:
        return self._combine(other, " && ", False)

    def __rand__(self, other: SearchQueryCombinable) -> CombinedSearchQuery:
        return self._combine(other, " && ", True)


class SearchQuery(SearchQueryCombinable, Expression):
    SEARCH_TYPES = {
        "plain": "PLAINTO_TSQUERY",
        "phrase": "PHRASETO_TSQUERY",
        "raw": "TO_TSQUERY",
        "websearch": "WEBSEARCH_TO_TSQUERY",
    }

    def __init__(
        self,
        value: QueryInput,
        config: ConfigInput | None = None,
        search_type: str = "plain",
        invert: bool = False,
    ) -> None:
        if isinstance(value, LexemeCombinable):
            search_type = "raw"
        function = self.SEARCH_TYPES.get(search_type)
        if function is None:
            raise ValueError(f"Unknown search_type argument '{search_type}'.")
        self.function = function
        self.value = value
        self.config = config
        self.invert = invert

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        value_result = _resolve_expression(self.value, resolve_context, treat_str_as_field=False)
        joins = value_result.joins
        args = [value_result.term]
        if self.config is not None:
            config_result = _resolve_expression(
                self.config, resolve_context, treat_str_as_field=False
            )
            args = [config_result.term, value_result.term]
            joins = _merge_joins(joins, config_result.joins)

        term: Term = PypikaFunction(self.function, *args)
        if self.invert:
            term = _TsQueryInvert(term)
        return ResolveResult(term=term, joins=joins)

    def __invert__(self) -> SearchQuery:
        return SearchQuery(
            self.value,
            config=self.config,
            search_type="raw" if isinstance(self.value, LexemeCombinable) else self._search_type,
            invert=not self.invert,
        )

    @property
    def _search_type(self) -> str:
        for key, value in self.SEARCH_TYPES.items():
            if value == self.function:
                return key
        return "plain"


class CombinedSearchQuery(SearchQueryCombinable, Expression):
    def __init__(
        self, left: SearchQueryCombinable, operator: str, right: SearchQueryCombinable
    ) -> None:
        self.left = left
        self.right = right
        self.operator = operator

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        left = self.left.resolve(resolve_context)
        right = self.right.resolve(resolve_context)
        term = _TsInfixOperator(left.term, self.operator, right.term)
        return ResolveResult(term=term, joins=_merge_joins(left.joins, right.joins))


class SearchRank(Expression):
    def __init__(
        self,
        vector: VectorInput,
        query: QueryInput,
        weights: RankWeightInput | None = None,
        normalization: NormalizationInput | None = None,
        cover_density: bool = False,
    ) -> None:
        self.vector = vector
        self.query = query
        self.weights = weights
        self.normalization = normalization
        self.cover_density = cover_density

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        vector_expr = (
            self.vector
            if isinstance(self.vector, (Expression, Term))
            else SearchVector(self.vector)
        )
        query_expr = (
            self.query if isinstance(self.query, (Expression, Term)) else SearchQuery(self.query)
        )
        vector_result = _resolve_expression(vector_expr, resolve_context, treat_str_as_field=False)
        query_result = _resolve_expression(query_expr, resolve_context, treat_str_as_field=False)

        args = [vector_result.term, query_result.term]
        joins = _merge_joins(vector_result.joins, query_result.joins)

        if self.weights is not None:
            weights_result = _resolve_expression(
                self.weights, resolve_context, treat_str_as_field=False
            )
            args = [weights_result.term, *args]
            joins = _merge_joins(joins, weights_result.joins)

        if self.normalization is not None:
            normalization_result = _resolve_expression(
                self.normalization, resolve_context, treat_str_as_field=False
            )
            args.append(normalization_result.term)
            joins = _merge_joins(joins, normalization_result.joins)

        function = "TS_RANK_CD" if self.cover_density else "TS_RANK"
        term = PypikaFunction(function, *args)
        return ResolveResult(term=term, joins=joins, output_field=FloatField())


def _format_headline_option_value(value: HeadlineOptionValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


class SearchHeadline(Expression):
    def __init__(
        self,
        expression: HeadlineExpressionInput,
        query: QueryInput,
        config: ConfigInput | None = None,
        start_sel: str | None = None,
        stop_sel: str | None = None,
        max_words: int | None = None,
        min_words: int | None = None,
        short_word: int | None = None,
        highlight_all: bool | None = None,
        max_fragments: int | None = None,
        fragment_delimiter: str | None = None,
    ) -> None:
        self.expression = expression
        self.query = query
        self.config = config
        self.options = {
            "StartSel": start_sel,
            "StopSel": stop_sel,
            "MaxWords": max_words,
            "MinWords": min_words,
            "ShortWord": short_word,
            "HighlightAll": highlight_all,
            "MaxFragments": max_fragments,
            "FragmentDelimiter": fragment_delimiter,
        }

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        expression_result = _resolve_expression(
            self.expression, resolve_context, treat_str_as_field=True
        )
        query_expr = (
            self.query if isinstance(self.query, (Expression, Term)) else SearchQuery(self.query)
        )
        query_result = _resolve_expression(query_expr, resolve_context, treat_str_as_field=False)

        args = [expression_result.term, query_result.term]
        joins = _merge_joins(expression_result.joins, query_result.joins)

        if self.config is not None:
            config_result = _resolve_expression(
                self.config, resolve_context, treat_str_as_field=False
            )
            args = [config_result.term, *args]
            joins = _merge_joins(joins, config_result.joins)

        options = {key: value for key, value in self.options.items() if value is not None}
        if options:
            options_sql = ", ".join(
                f"{key}={_format_headline_option_value(value)}" for key, value in options.items()
            )
            args.append(ValueWrapper(options_sql))

        term = PypikaFunction("TS_HEADLINE", *args)
        return ResolveResult(term=term, joins=joins, output_field=TextField())


class LexemeCombinable(Expression):
    def _combine(self, other: LexemeCombinable, operator: str, reversed: bool) -> CombinedLexeme:
        if not isinstance(other, LexemeCombinable):
            raise TypeError(
                "A Lexeme can only be combined with another Lexeme, "
                f"got {other.__class__.__name__}."
            )
        if reversed:
            return CombinedLexeme(other, operator, self)
        return CombinedLexeme(self, operator, other)

    def __or__(self, other: LexemeCombinable) -> CombinedLexeme:
        return self._combine(other, " | ", False)

    def __ror__(self, other: LexemeCombinable) -> CombinedLexeme:
        return self._combine(other, " | ", True)

    def __and__(self, other: LexemeCombinable) -> CombinedLexeme:
        return self._combine(other, " & ", False)

    def __rand__(self, other: LexemeCombinable) -> CombinedLexeme:
        return self._combine(other, " & ", True)

    def _as_tsquery(self) -> str:
        raise NotImplementedError

    def __invert__(self) -> LexemeCombinable:
        raise NotImplementedError


class Lexeme(LexemeCombinable, Expression):
    def __init__(
        self,
        value: str,
        invert: bool = False,
        prefix: bool = False,
        weight: str | None = None,
    ) -> None:
        if value == "":
            raise ValueError("Lexeme value cannot be empty.")
        if not isinstance(value, str):
            raise TypeError(f"Lexeme value must be a string, got {value.__class__.__name__}.")
        if weight is not None and weight.lower() not in {"a", "b", "c", "d"}:
            raise ValueError(f"Weight must be one of 'A', 'B', 'C', and 'D', got {weight!r}.")
        self.value = value
        self.invert = invert
        self.prefix = prefix
        self.weight = weight

    def _as_tsquery(self) -> str:
        token = "'" + self.value.replace("'", "''") + "'"
        label = ""
        if self.prefix:
            label += "*"
        if self.weight:
            label += self.weight
        if label:
            token = f"{token}:{label}"
        if self.invert:
            token = f"!{token}"
        return token

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        return ResolveResult(term=ValueWrapper(self._as_tsquery()))

    def __invert__(self) -> Lexeme:
        return Lexeme(
            self.value,
            invert=not self.invert,
            prefix=self.prefix,
            weight=self.weight,
        )


class CombinedLexeme(LexemeCombinable, Expression):
    def __init__(self, left: LexemeCombinable, operator: str, right: LexemeCombinable) -> None:
        self.left = left
        self.right = right
        self.operator = operator

    def _as_tsquery(self) -> str:
        return f"({self.left._as_tsquery()}{self.operator}{self.right._as_tsquery()})"

    def resolve(self, resolve_context: ResolveContext) -> ResolveResult:
        return ResolveResult(term=ValueWrapper(self._as_tsquery()))

    def __invert__(self) -> CombinedLexeme:
        operator = " & " if self.operator == " | " else " | "
        return CombinedLexeme(~self.left, operator, ~self.right)
