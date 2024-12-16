from tests import testmodels
from tortoise.contrib import test


class TestPosixRegexFilter(test.TestCase):

    @test.requireCapability(dialect="postgres")
    async def test_regex_filter_postgres(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(
                await testmodels.Author.filter(
                    name__posix_regex="^Johann [a-zA-Z]+ von Goethe$"
                ).values_list("name", flat=True)
            ),
            {author.name},
        )

    @test.requireCapability(dialect="mysql")
    async def test_regex_filter_mysql(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(
                await testmodels.Author.filter(
                    name__posix_regex="^Johann [a-zA-Z]+ von Goethe$"
                ).values_list("name", flat=True)
            ),
            {author.name},
        )

    @test.requireCapability(dialect="sqlite")
    async def test_regex_filter_sqlite(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(
                await testmodels.Author.filter(
                    name__posix_regex="^Johann [a-zA-Z]+ von Goethe$"
                ).values_list("name", flat=True)
            ),
            {author.name},
        )

    @test.requireCapability(dialect="postgres")
    async def test_regex_filter_works_with_null_field_postgres(self):
        await testmodels.Tournament.create(name="Test")
        print(testmodels.Tournament.filter(desc__posix_regex="^test$").sql())
        self.assertEqual(
            set(
                await testmodels.Tournament.filter(desc__posix_regex="^test$").values_list(
                    "name", flat=True
                )
            ),
            set(),
        )

    @test.requireCapability(dialect="sqlite")
    async def test_regex_filter_works_with_null_field_sqlite(self):
        await testmodels.Tournament.create(name="Test")
        print(testmodels.Tournament.filter(desc__posix_regex="^test$").sql())
        self.assertEqual(
            set(
                await testmodels.Tournament.filter(desc__posix_regex="^test$").values_list(
                    "name", flat=True
                )
            ),
            set(),
        )


class TestCaseInsensitivePosixRegexFilter(test.TestCase):
    @test.requireCapability(dialect="postgres")
    async def test_case_insensitive_regex_filter_postgres(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(
                await testmodels.Author.filter(
                    name__iposix_regex="^johann [a-zA-Z]+ Von goethe$"
                ).values_list("name", flat=True)
            ),
            {author.name},
        )

    @test.requireCapability(dialect="sqlite")
    async def test_case_insensitive_regex_filter_sqlite(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(
                await testmodels.Author.filter(
                    name__iposix_regex="^johann [a-zA-Z]+ Von goethe$"
                ).values_list("name", flat=True)
            ),
            {author.name},
        )
