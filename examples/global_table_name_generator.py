"""
This example demonstrates how to use the global table name generator to automatically
generate snake_case table names for all models, and how explicit table names take precedence.
"""

from tortoise import Tortoise, fields, run_async
from tortoise.models import Model


def snake_case_table_names(cls):
    """Convert CamelCase class name to snake_case table name"""
    name = cls.__name__
    return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")


class UserProfile(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BlogPost(Model):
    id = fields.IntField(primary_key=True)
    title = fields.TextField()
    author: fields.ForeignKeyRelation[UserProfile] = fields.ForeignKeyField(
        "models.UserProfile", related_name="posts"
    )

    class Meta:
        table = "custom_blog_posts"

    def __str__(self):
        return self.title


async def run():
    # Initialize with snake_case table name generator
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["__main__"]},
        table_name_generator=snake_case_table_names,
    )
    await Tortoise.generate_schemas()

    # UserProfile uses generated name, BlogPost uses explicit table name
    print(f"UserProfile table name: {UserProfile._meta.db_table}")  # >>> user_profile
    print(f"BlogPost table name: {BlogPost._meta.db_table}")  # >>> custom_blog_posts

    await Tortoise.close_connections()


if __name__ == "__main__":
    run_async(run())
