from tests.testmodels import Post, Comment, Favorite
from tortoise.contrib import test
from tortoise.functions import Count


class TestAggregationWithDistinct(test.TestCase):
    async def test_aggregation_with_distinct(self):
        dummy_post = await Post.create(name="Dummy post")
        await Comment.create(content='Dummy comment 1', post=dummy_post)
        await Comment.create(content='Dummy comment 2', post=dummy_post)
        await Favorite.create(post=dummy_post)

        post = await Post.create(name="Post 1")
        await Comment.create(content='Comment 1', post=post)
        await Comment.create(content='Comment 2', post=post)
        await Comment.create(content='Comment 3', post=post)
        await Favorite.create(post=post)
        await Favorite.create(post=post)

        school_with_count = await Post.filter(
            id=post.id
        ).annotate(
            comments_count=Count("comments"),
            favorites_count=Count("favorites")
        ).first()

        self.assertEqual(school_with_count.comments_count, 6)
        self.assertEqual(school_with_count.favorites_count, 6)
        # comments_count and favorites_count will same if no distinct

        school_with_distinct_count = await Post.filter(
            id=post.id
        ).annotate(
            comments_count=Count("comments", distinct=True),
            favorites_count=Count("favorites", distinct=True)
        ).first()

        self.assertEqual(school_with_distinct_count.comments_count, 3)
        self.assertEqual(school_with_distinct_count.favorites_count, 2)
