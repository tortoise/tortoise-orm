from tortoise import Model, Tortoise, fields, run_async
from tortoise.functions import Avg, Count, Sum


class Author(Model):
    name = fields.CharField(max_length=255)


class Book(Model):
    name = fields.CharField(max_length=255)
    author = fields.ForeignKeyField("models.Author", related_name="books")
    rating = fields.FloatField()


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    a1 = await Author.create(name="author1")
    a2 = await Author.create(name="author2")
    for i in range(10):
        await Book.create(name=f"book{i}", author=a1, rating=i)
    for i in range(5):
        await Book.create(name=f"book{i}", author=a2, rating=i)

    ret = await Book.annotate(count=Count("id")).group_by("author_id").values("author_id", "count")
    print(ret)
    # >>> [{'author_id': 1, 'count': 10}, {'author_id': 2, 'count': 5}]

    ret = (
        await Book.annotate(count=Count("id"))
        .filter(count__gt=6)
        .group_by("author_id")
        .values("author_id", "count")
    )
    print(ret)
    # >>> [{'author_id': 1, 'count': 10}]

    ret = await Book.annotate(sum=Sum("rating")).group_by("author_id").values("author_id", "sum")
    print(ret)
    # >>> [{'author_id': 1, 'sum': 45.0}, {'author_id': 2, 'sum': 10.0}]

    ret = (
        await Book.annotate(sum=Sum("rating"))
        .filter(sum__gt=11)
        .group_by("author_id")
        .values("author_id", "sum")
    )
    print(ret)
    # >>> [{'author_id': 1, 'sum': 45.0}]

    ret = await Book.annotate(avg=Avg("rating")).group_by("author_id").values("author_id", "avg")
    print(ret)
    # >>> [{'author_id': 1, 'avg': 4.5}, {'author_id': 2, 'avg': 2.0}]

    ret = (
        await Book.annotate(avg=Avg("rating"))
        .filter(avg__gt=3)
        .group_by("author_id")
        .values("author_id", "avg")
    )
    print(ret)
    # >>> [{'author_id': 1, 'avg': 4.5}]

    # and use .values_list()
    ret = (
        await Book.annotate(count=Count("id"))
        .group_by("author_id")
        .values_list("author_id", "count")
    )
    print(ret)
    # >>> [(1, 10), (2, 5)]

    # group by with join
    ret = (
        await Book.annotate(count=Count("id"))
        .group_by("author__name")
        .values("author__name", "count")
    )
    print(ret)
    # >>> [{"author__name": "author1", "count": 10}, {"author__name": "author2", "count": 5}]


if __name__ == "__main__":
    run_async(run())
