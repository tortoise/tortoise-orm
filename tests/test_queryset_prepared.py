from tests.testmodels import (
    Author,
)
from tortoise.contrib import test
from tortoise.expressions import Subquery, Q
from tortoise.parameter import Parameter


class TestQuerysetPrepared(test.TestCase):
    def test_prepared_queryset_always_same(self):
        cache_key = "test_prepared_queryset_always_same"
        prepared = Author.prepare_sql(cache_key).filter(id=Parameter("some_param")).prepared()
        assert Author.prepare_sql(cache_key) is prepared

    def test_disallow_filtering_on_prepared_queryset(self):
        cache_key = "test_disallow_filtering_on_prepared_queryset"
        prepared = Author.prepare_sql(cache_key).filter(id=Parameter("some_param")).prepared()

        with self.assertRaises(ValueError):
            prepared.filter(id=1)

    async def test_gte_filter(self):
        author1 = await Author.create(name="1")
        author2 = await Author.create(name="2")
        author3 = await Author.create(name="3")

        expected = await Author.filter(id__gte=author2.pk).order_by("id")

        prepared = Author.prepare_sql("test_gte_filter").filter(id__gte=Parameter("idgte")).order_by("id").prepared()
        actual = await prepared.execute(idgte=author2.pk)
        self.assertEqual(len(actual), 2)
        self.assertEqual(actual[0].id, author2.pk)
        self.assertEqual(actual[1].id, author3.pk)
        self.assertEqual(expected, actual)

    async def test_string_param(self):
        author1 = await Author.create(name="1")
        author2 = await Author.create(name="2")
        author3 = await Author.create(name="3")

        expected = await Author.filter(name=author2.name)

        prepared = Author.prepare_sql("test_string_param").filter(name=Parameter("name")).prepared()
        actual = await prepared.execute(name=author2.name)
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0].id, author2.pk)
        self.assertEqual(expected, actual)

    async def test_startswith_filter(self):
        author1 = await Author.create(name="test")
        author2 = await Author.create(name="testqwe")
        author3 = await Author.create(name="qwetest")

        prepared = Author.prepare_sql("test_startswith_filter").filter(name__startswith=Parameter("name")).prepared()

        for test_name in (author2.pk, author1.name, author3.name, "asd"):
            expected = await Author.filter(name__startswith=test_name)
            actual = await prepared.execute(name=test_name)
            self.assertEqual(expected, actual)

    async def test_in_filter(self):
        author1 = await Author.create(name="test")
        author2 = await Author.create(name="testqwe")
        author3 = await Author.create(name="qwetest")

        prepared = Author.prepare_sql("test_in_filter").filter(id__in=Parameter("ids")).prepared()

        for test_ids in (
                [author2.pk, author1.pk],
                [author3.pk, author3.pk * 2, author3.pk * 10]
        ):
            expected = await Author.filter(id__in=test_ids)
            actual = await prepared.execute(ids=test_ids)
            self.assertEqual(expected, actual)

    async def test_subqueries(self):
        author1 = await Author.create(name="1")
        author2 = await Author.create(name="2")
        author3 = await Author.create(name="3")

        prepared = Author.prepare_sql("test_subqueries").filter(id__in=Subquery(
            Author.filter(Q(id=Parameter("id1")) | Q(id=Parameter("id2"))).values("id")
        )).prepared()

        for id1, id2 in (
                (author2.pk, author1.pk),
                (author3.pk, author3.pk * 2),
        ):
            expected = await Author.filter(id__in=Subquery(
                Author.filter(Q(id=id1) | Q(id=id2)).values("id")
            ))
            actual = await prepared.execute(id1=id1, id2=id2)
            self.assertEqual(expected, actual)

    async def test_subqueries_in_filter(self):
        author1 = await Author.create(name="1")
        author2 = await Author.create(name="2")
        author3 = await Author.create(name="3")

        prepared = Author.prepare_sql("test_subqueries_in_filter").filter(id__in=Subquery(
            Author.filter(id__in=Parameter("ids")).values("id")
        )).prepared()

        for test_ids in (
                [author2.pk, author1.pk],
                [author3.pk, author3.pk * 2, author3.pk * 10]
        ):
            expected = await Author.filter(id__in=Subquery(
                Author.filter(id__in=test_ids).values("id")
            ))
            actual = await prepared.execute(ids=test_ids)
            self.assertEqual(expected, actual)

    async def test_update(self):
        author1 = await Author.create(name="1")
        author2 = await Author.create(name="2")
        author3 = await Author.create(name="3")

        original_name1 = author1.name
        original_name2 = author2.name
        new_name1 =  f"{author1.name}_test"

        prepared = Author.prepare_sql("test_update").filter(
            id=Parameter("search_id")
        ).update(name=Parameter("replace_name")).prepared()

        await prepared.execute(search_id=author1.pk, replace_name=new_name1)
        await author1.refresh_from_db(["name"])
        await author2.refresh_from_db(["name"])
        self.assertEqual(author1.name, new_name1)
        self.assertEqual(author2.name, original_name2)

        await prepared.execute(search_id=author1.pk, replace_name=original_name1)
        await author1.refresh_from_db(["name"])
        self.assertEqual(author1.name, original_name1)

    async def test_delete(self):
        author1 = await Author.create(name="1")
        author2 = await Author.create(name="2")
        author3 = await Author.create(name="3")

        prepared = Author.prepare_sql("test_delete").filter(
            id__in=Parameter("ids"),
        ).delete().prepared()

        affected = await prepared.execute(ids=[author1.pk])
        self.assertEqual(affected, 1)
        self.assertEqual(await Author.all().count(), 2)
        existing = await Author.all().values_list("id", flat=True)
        self.assertEqual(set(existing), {author2.pk, author3.pk})

    async def test_exists(self):
        author1 = await Author.create(name="1")
        author2 = await Author.create(name="2")
        author3 = await Author.create(name="3")

        prepared = Author.prepare_sql("test_exists").filter(
            id__in=Parameter("ids"),
        ).exists().prepared()

        self.assertTrue(await prepared.execute(ids=[author1.pk]))
        self.assertFalse(await prepared.execute(ids=[author3.pk * 2]))
