from typing import List, Optional, Type

from tests.testmodels import Author
from tortoise import BaseDBAsyncClient
from tortoise.contrib import test
from tortoise.signals import post_delete, post_save, pre_delete, pre_save


@pre_save(Author)
async def author_pre_save(
    sender: "Type[Author]", instance: Author, using_db, update_fields
) -> None:
    await Author.filter(name="test1").update(name="test_pre-save")


@post_save(Author)
async def author_post_save(
    sender: "Type[Author]",
    instance: Author,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List,
) -> None:
    await Author.filter(name="test2").update(name="test_post-save")


@pre_delete(Author)
async def author_pre_delete(
    sender: "Type[Author]", instance: Author, using_db: "Optional[BaseDBAsyncClient]"
) -> None:
    await Author.filter(name="test3").update(name="test_pre-delete")


@post_delete(Author)
async def author_post_delete(
    sender: "Type[Author]", instance: Author, using_db: "Optional[BaseDBAsyncClient]"
) -> None:
    await Author.filter(name="test4").update(name="test_post-delete")


class TestSignals(test.TestCase):
    async def setUp(self):
        self.author_save = await Author.create(name="author_save")
        self.author_delete = await Author.create(name="author_delete")

        self.author1 = await Author.create(name="test1")
        self.author2 = await Author.create(name="test2")
        self.author3 = await Author.create(name="test3")
        self.author4 = await Author.create(name="test4")

    async def test_save(self):
        author_save = await Author.get(pk=self.author_save.pk)
        author_save.name = "test-save"
        await author_save.save()

        author1 = await Author.get(pk=self.author1.pk)
        author2 = await Author.get(pk=self.author2.pk)

        self.assertEqual(author1.name, "test_pre-save")
        self.assertEqual(author2.name, "test_post-save")

    async def test_delete(self):
        author_delete = await Author.get(pk=self.author_delete.pk)
        await author_delete.delete()

        author3 = await Author.get(pk=self.author3.pk)
        author4 = await Author.get(pk=self.author4.pk)

        self.assertEqual(author3.name, "test_pre-delete")
        self.assertEqual(author4.name, "test_post-delete")
