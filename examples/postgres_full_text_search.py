"""
Showcase PostgreSQL full text search helpers.
Requires PostgreSQL 12+ for generated TSVECTOR columns.
"""

from tortoise import Tortoise, fields, run_async
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise.contrib.postgres.indexes import GinIndex
from tortoise.contrib.postgres.search import (
    Lexeme,
    SearchHeadline,
    SearchQuery,
    SearchRank,
    SearchVector,
)
from tortoise.expressions import F
from tortoise.models import Model


class Article(Model):
    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=200)
    body = fields.TextField()
    search = TSVectorField(
        source_fields=("title", "body"),
        config="english",
        weights=("A", "B"),
        stored=True,
    )

    class Meta:
        indexes = [GinIndex(fields=("search",))]

    def __str__(self):
        return self.title


async def run() -> None:
    await Tortoise.init(
        {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": "localhost",
                        "port": "5432",
                        "user": "tortoise",
                        "password": "qwerty123",
                        "database": "test",
                    },
                }
            },
            "apps": {"models": {"models": ["__main__"], "default_connection": "default"}},
        },
        _create_db=True,
    )

    try:
        await Tortoise.generate_schemas()

        await Article.create(
            title="Postgres search with Tortoise",
            body="Full text search in Postgres is fast and powerful.",
        )
        await Article.create(
            title="SQLite basics",
            body="This article does not talk about Postgres at all.",
        )

        print("Plain __search on a text field")
        titles = await Article.filter(title__search="postgres search").values_list(
            "title", flat=True
        )
        print(list(titles))

        web_query = SearchQuery("postgres search", search_type="websearch", config="english")
        lexeme_query = SearchQuery(Lexeme("tort", prefix=True) & ~Lexeme("slow"))
        combined_query = web_query | lexeme_query

        vector = SearchVector("title", "body", config="english")
        rank = SearchRank(vector, combined_query, normalization=32)
        headline = SearchHeadline(
            "body",
            combined_query,
            start_sel="<<",
            stop_sel=">>",
            max_words=12,
            min_words=4,
        )

        results = (
            await Article.annotate(rank=rank, snippet=headline)
            .filter(search__search=combined_query)
            .order_by("-rank")
            .values("title", "rank", "snippet")
        )

        print("Ranked full-text search results")
        for row in results:
            print(row["title"], row["rank"], row["snippet"])

        stored_rank = SearchRank(F("search"), combined_query)
        stored_results = (
            await Article.annotate(rank=stored_rank)
            .filter(search__search=combined_query)
            .order_by("-rank")
            .values("title", "rank")
        )
        print("Ranked results using stored TSVECTOR")
        for row in stored_results:
            print(row["title"], row["rank"])
    finally:
        await Tortoise._drop_databases()


if __name__ == "__main__":
    run_async(run())
