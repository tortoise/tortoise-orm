"""
This example demonstrates most basic operations with single model
"""
from tortoise import Tortoise, fields, run_async
from tortoise.contrib.mysql.indexes import FullTextIndex
from tortoise.contrib.mysql.search import SearchCriterion
from tortoise.models import Model


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    datetime = fields.DatetimeField(null=True)

    class Meta:
        table = "event"
        indexes = [FullTextIndex(fields={"name"})]

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(
        db_url="mysql://root:123456@127.0.0.1:3306/test", modules={"models": ["__main__"]}
    )
    # await Tortoise.generate_schemas()

    ret = Event.filter(id__search="test").sql()
    print(ret)


if __name__ == "__main__":
    run_async(run())
