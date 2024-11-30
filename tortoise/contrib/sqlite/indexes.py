from typing import Dict, Optional, Tuple

from pypika.terms import Term, ValueWrapper

from tortoise.indexes import PartialIndex


class SqliteIndex(PartialIndex):
    INDEX_CREATE_TEMPLATE = PartialIndex.INDEX_CREATE_TEMPLATE.replace("INDEX", "INDEX {exists} ")


class SqliteUniqueIndex(SqliteIndex):
    INDEX_TYPE = "unique".upper()

    def __init__(
        self,
        *expressions: Term,
        fields: Optional[Tuple[str, ...]] = None,
        name: Optional[str] = None,
        condition: Optional[Dict[str, str]] = None,
        where_expre: Optional[str] = None,
    ):
        _condition = condition
        if condition:
            condition = None
        super().__init__(*expressions, fields=fields, name=name, condition=condition)
        if _condition:
            # TODO: what is the best practice to inject where expression?
            self.extra = where_expre or self._gen_condition(_condition)

    @classmethod
    def _gen_field_cond(cls, kv: tuple):
        key, cond = kv
        op = (
            ""
            if isinstance(cond, str)
            and cond.strip().lower().startswith(("is ", "isnot ", "<", ">", "=", "!="))
            else "="
        )
        if op == "=":
            cond = ValueWrapper(cond)
        return str(f"{key} {op} {cond}")

    def _gen_condition(self, conditions: Dict[str, str]):
        conditions = " AND ".join(tuple(map(self._gen_field_cond, conditions.items())))
        return f" where {conditions}"
