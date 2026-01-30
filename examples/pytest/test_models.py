"""
Example pytest tests demonstrating Tortoise ORM testing patterns.

Run with: pytest examples/pytest/test_models.py -v
"""

import pytest


@pytest.mark.asyncio
class TestUserModel:
    """Tests for the User model."""

    async def test_create_user(self, db):
        """Test creating a user."""
        from examples.pytest.models import User

        user = await User.create(
            username="newuser",
            email="newuser@example.com",
        )

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True

    async def test_user_str(self, db):
        """Test user string representation."""
        from examples.pytest.models import User

        user = await User.create(username="testuser", email="test@example.com")
        assert str(user) == "testuser"

    async def test_get_user(self, db):
        """Test retrieving a user."""
        from examples.pytest.models import User

        created = await User.create(username="findme", email="find@example.com")
        found = await User.get(id=created.id)

        assert found.username == "findme"
        assert found.email == "find@example.com"

    async def test_update_user(self, db):
        """Test updating a user."""
        from examples.pytest.models import User

        user = await User.create(username="original", email="original@example.com")
        user.username = "updated"
        await user.save()

        refreshed = await User.get(id=user.id)
        assert refreshed.username == "updated"

    async def test_delete_user(self, db):
        """Test deleting a user."""
        from examples.pytest.models import User

        user = await User.create(username="deleteme", email="delete@example.com")
        user_id = user.id
        await user.delete()

        assert await User.filter(id=user_id).count() == 0

    async def test_filter_users(self, db):
        """Test filtering users."""
        from examples.pytest.models import User

        await User.create(username="active1", email="a1@example.com", is_active=True)
        await User.create(username="active2", email="a2@example.com", is_active=True)
        await User.create(username="inactive", email="i@example.com", is_active=False)

        active_users = await User.filter(is_active=True).all()
        assert len(active_users) == 2

        inactive_users = await User.filter(is_active=False).all()
        assert len(inactive_users) == 1


@pytest.mark.asyncio
class TestWithPreloadedUser:
    """Tests using the db_with_user fixture."""

    async def test_user_exists(self, db_with_user):
        """Test that the pre-created user exists."""
        from examples.pytest.models import User

        user = db_with_user
        assert user.username == "testuser"

        # Verify it's in the database
        found = await User.get(id=user.id)
        assert found.username == "testuser"

    async def test_can_create_additional_users(self, db_with_user):
        """Test creating additional users alongside the fixture user."""
        from examples.pytest.models import User

        await User.create(username="another", email="another@example.com")

        count = await User.all().count()
        assert count == 2  # fixture user + new user


@pytest.mark.asyncio
class TestPostModel:
    """Tests for the Post model with relations."""

    async def test_create_post_with_author(self, db):
        """Test creating a post with an author."""
        from examples.pytest.models import Post, User

        author = await User.create(username="writer", email="writer@example.com")
        post = await Post.create(
            title="My First Post",
            content="Hello, World!",
            author=author,
        )

        assert post.id is not None
        assert post.title == "My First Post"

    async def test_post_author_relation(self, db):
        """Test accessing post's author relation."""
        from examples.pytest.models import Post, User

        author = await User.create(username="blogger", email="blog@example.com")
        post = await Post.create(
            title="Blog Post",
            content="Some content",
            author=author,
        )

        # Fetch post with author
        fetched = await Post.get(id=post.id).prefetch_related("author")
        assert fetched.author.username == "blogger"

    async def test_user_posts_relation(self, db):
        """Test accessing user's posts via reverse relation."""
        from examples.pytest.models import Post, User

        author = await User.create(username="prolific", email="prolific@example.com")
        await Post.create(title="Post 1", content="Content 1", author=author)
        await Post.create(title="Post 2", content="Content 2", author=author)

        # Fetch user with posts
        user = await User.get(id=author.id).prefetch_related("posts")
        assert len(user.posts) == 2


@pytest.mark.asyncio
class TestWithPreloadedPosts:
    """Tests using the db_with_posts fixture."""

    async def test_posts_exist(self, db_with_posts):
        """Test that pre-created posts exist."""
        from examples.pytest.models import Post

        data = db_with_posts
        assert len(data["posts"]) == 3

        count = await Post.all().count()
        assert count == 3

    async def test_posts_belong_to_author(self, db_with_posts):
        """Test that all posts belong to the fixture author."""
        from examples.pytest.models import Post

        data = db_with_posts
        author = data["user"]

        posts = await Post.filter(author=author).all()
        assert len(posts) == 3

    async def test_can_add_more_posts(self, db_with_posts):
        """Test adding more posts to the fixture author."""
        from examples.pytest.models import Post

        data = db_with_posts
        author = data["user"]

        await Post.create(title="New Post", content="New content", author=author)

        count = await Post.filter(author=author).count()
        assert count == 4


@pytest.mark.asyncio
async def test_database_isolation(db):
    """
    Test that each test gets an isolated database.

    This test creates data that should NOT appear in other tests.
    """
    from examples.pytest.models import User

    await User.create(username="isolated_user", email="isolated@example.com")
    count = await User.all().count()
    assert count == 1  # Only this test's user


@pytest.mark.asyncio
async def test_database_is_empty(db):
    """
    Test that database starts empty.

    This verifies isolation - data from other tests should not be present.
    """
    from examples.pytest.models import Post, User

    user_count = await User.all().count()
    post_count = await Post.all().count()

    assert user_count == 0
    assert post_count == 0
