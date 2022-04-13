from pypika import Parameter

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.fields import BigIntField, IntField, SmallIntField


class ODBCExecutor(BaseExecutor):
    def parameter(self, pos: int) -> Parameter:
        return Parameter("?")

    async def _process_insert_result(self, instance: Model, results: int) -> None:
        pk_field_object = self.model._meta.pk
        if (
            isinstance(pk_field_object, (SmallIntField, IntField, BigIntField))
            and pk_field_object.generated
        ):
            instance.pk = results
