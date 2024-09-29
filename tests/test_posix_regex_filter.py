from tests import testmodels
from tortoise.contrib import test


class TestPosixRegexFilter(test.TestCase):

    @test.requireCapability(dialect="mysql")
    @test.requireCapability(dialect="postgres")
    async def test_regex_filter(self):
        author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
        self.assertEqual(
            set(
                await testmodels.Author.filter(
                    name__posix_regex="^Johann [a-zA-Z]+ von Goethe$"
                ).values_list("name", flat=True)
            ),
            {author.name},
        )
