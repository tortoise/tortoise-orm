from tortoise.contrib import test
from tests import testmodels

@test.requireCapability(dialect="postgres")
class TestPosixRegexFilterPostgres(test.IsolatedTestCase):
    tortoise_test_modules = ["tests.testmodels"]

    async def test_regex_filter(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(await testmodels.Author.filter(name__posix_regex="^Johann [a-zA-Z]+ von Goethe$").values_list("name", flat=True)),
            {"Johann Wolfgang von Goethe"},
        )


@test.requireCapability(dialect="mysql")
class TestPosixRegexFilterPostgres(test.IsolatedTestCase):
    tortoise_test_modules = ["tests.testmodels"]

    async def test_regex_filter(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(await testmodels.Author.filter(name__posix_regex="^Johann [a-zA-Z]+ von Goethe$").values_list("name", flat=True)),
            {"Johann Wolfgang von Goethe"},
        )