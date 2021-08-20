"""
This example demonstrates most basic operations with single model
"""
from tortoise import Tortoise, fields, run_async
from tortoise.manager import Manager
from tortoise.models import Model
from tortoise.queryset import QuerySet


class StatusQuerySet(QuerySet):
    def active(self):
        return self.filter(status=1)


class StatusManager(Manager):
    def __init__(self, model=None, queryset_cls=None) -> None:
        super().__init__(model=model)
        self.queryset_cls = queryset_cls or QuerySet

    def get_queryset(self):
        return self.queryset_cls(self._model)


class AbstractManagerModel(Model):
    all_objects = Manager()

    class Meta:
        abstract = True


class ManagerModel(AbstractManagerModel):
    status = fields.IntField(default=0)

    class Meta:
        manager = StatusManager(queryset_cls=StatusQuerySet)


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    m1 = await ManagerModel.create()
    m2 = await ManagerModel.create(status=1)

    assert await ManagerModel.all().active().count() == 1
    assert await ManagerModel.all_objects.count() == 2

    assert await ManagerModel.all().active().get_or_none(pk=m1.pk) is None
    assert await ManagerModel.all_objects.get_or_none(pk=m1.pk) is not None
    assert await ManagerModel.get_or_none(pk=m2.pk) is not None


if __name__ == "__main__":
    run_async(run())
