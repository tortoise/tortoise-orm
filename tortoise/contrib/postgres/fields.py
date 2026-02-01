from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from tortoise.exceptions import ConfigurationError
from tortoise.fields import Field


class TSVectorField(Field):
    SQL_TYPE = "TSVECTOR"
    allows_generated = True

    def __init__(
        self,
        source_fields: Sequence[str] | str | None = None,
        config: str | None = None,
        weights: Sequence[str] | None = None,
        stored: bool = True,
        **kwargs: Any,
    ) -> None:
        if isinstance(source_fields, str):
            source_fields = (source_fields,)
        self.source_fields = tuple(source_fields or ())
        if not self.source_fields and stored:
            stored = False
        if "generated" in kwargs and kwargs["generated"] != stored:
            raise ConfigurationError("TSVectorField 'generated' must match 'stored' when provided.")
        generated = kwargs.pop("generated", stored)
        if generated and not self.source_fields:
            raise ConfigurationError("TSVectorField generated columns require source_fields.")
        super().__init__(generated=generated, **kwargs)
        self.config = config
        self.weights = tuple(weights) if weights is not None else None
        self.stored = stored

        if self.weights and not self.source_fields:
            raise ConfigurationError("TSVectorField weights require source_fields.")
        if self.weights and len(self.weights) != len(self.source_fields):
            raise ConfigurationError("TSVectorField weights must match source_fields length.")

    def _quote_sql_literal(self, value: str) -> str:
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    def _to_tsvector_sql(self, db_field: str) -> str:
        field_sql = f"COALESCE(\"{db_field}\", '')"
        if self.config is not None:
            return f"TO_TSVECTOR({self._quote_sql_literal(self.config)},{field_sql})"
        return f"TO_TSVECTOR({field_sql})"

    def _get_generated_sql(self) -> str | None:
        if not self.stored:
            return None
        parts: list[str] = []
        for idx, field_name in enumerate(self.source_fields):
            field = self.model._meta.fields_map.get(field_name)
            if field is None:
                raise ConfigurationError(f"Unknown source field '{field_name}'.")
            if not field.has_db_field:
                raise ConfigurationError(
                    f"Source field '{field_name}' does not map to a database column."
                )
            db_field = field.source_field or field.model_field_name
            vector_sql = self._to_tsvector_sql(db_field)
            if self.weights is not None:
                weight = self._quote_sql_literal(self.weights[idx])
                vector_sql = f"SETWEIGHT({vector_sql},{weight})"
            parts.append(vector_sql)
        expression = " || ".join(parts)
        return f"GENERATED ALWAYS AS ({expression}) STORED"

    def describe(self, serializable: bool) -> dict:
        desc = super().describe(serializable)
        desc["source_fields"] = list(self.source_fields) if serializable else self.source_fields
        desc["config"] = self.config
        if self.weights is None:
            desc["weights"] = None
        else:
            desc["weights"] = list(self.weights) if serializable else self.weights
        desc["stored"] = self.stored
        return desc

    class _db_postgres:
        def __init__(self, field: TSVectorField) -> None:
            self.field = field

        @property
        def GENERATED_SQL(self) -> str | None:
            return self.field._get_generated_sql()


class ArrayField(Field, list):  # type: ignore
    def __init__(self, element_type: str = "int", **kwargs: Any):
        super().__init__(**kwargs)
        self.element_type = element_type.upper()

    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        return f"{self.element_type}[]"
