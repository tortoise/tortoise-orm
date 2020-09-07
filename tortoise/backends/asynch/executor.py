from typing import Any, Sequence

from pypika import Parameter

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.fields import BigIntField, IntField, SmallIntField


class AsynchExecutor(BaseExecutor):
    async def _process_insert_result(self, instance: "Model", results: Any) -> None:
        pk_field_object = self.model._meta.pk
        if (
            isinstance(pk_field_object, (SmallIntField, IntField, BigIntField))
            and pk_field_object.generated
        ):
            instance.pk = results

    def _prepare_insert_statement(self, columns: Sequence[str], has_generated: bool = True) -> str:
        return (
            str(
                self.db.query_class.into(self.model._meta.basetable)
                .columns(*columns)
                .insert(*[self.parameter(i) for i in range(len(columns))])
            ).split("VALUES")[0]
            + "VALUES"
        )

    def parameter(self, pos: int) -> Parameter:
        return Parameter("")
