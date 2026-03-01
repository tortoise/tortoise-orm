from __future__ import annotations

import json

import aiosqlite
from pypika_tortoise.terms import Criterion, Term, ValueWrapper
from pypika_tortoise.terms import Function as PypikaFunction


class SQLiteJSONContains(PypikaFunction):
    def __init__(self, column_name: Term, target: Term) -> None:
        super().__init__("json_contains", column_name, target)


def sqlite_json_contains(field: Term, value: str) -> Criterion:
    return SQLiteJSONContains(field, ValueWrapper(value))


def _json_contains_impl(target_str: str | None, candidate_str: str | None) -> bool:
    """Check if target JSON value contains the candidate JSON value.

    Semantics match PostgreSQL's @> operator:
    - Arrays: every element of candidate appears in target.
    - Objects: every key in candidate exists in target with a matching value.
    - Scalars: equality.
    """
    if target_str is None or candidate_str is None:
        return False
    try:
        target = json.loads(target_str)
        candidate = json.loads(candidate_str)
    except (json.JSONDecodeError, TypeError):
        return False
    return _contains(target, candidate)


def _contains(target: object, candidate: object) -> bool:
    if isinstance(candidate, dict):
        if not isinstance(target, dict):
            return False
        return all(k in target and _contains(target[k], v) for k, v in candidate.items())
    if isinstance(candidate, list):
        if not isinstance(target, list):
            return False
        return all(any(_contains(t, c) for t in target) for c in candidate)
    return target == candidate


async def install_json_functions(connection: aiosqlite.Connection) -> None:
    await connection.create_function("json_contains", 2, _json_contains_impl)
