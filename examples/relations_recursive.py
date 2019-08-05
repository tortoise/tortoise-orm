"""
This example shows how self-referential (recursive) relations work.

Key points in this example are:
* Use of ForeignKeyField that refers to self
* To pass in the (optional) parent node at creation
* To use async iterator to fetch children
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model


class User(Model):
    name = fields.CharField(max_length=50)
    parent = fields.ForeignKeyField("models.User", related_name="children", null=True)

    def __str__(self):
        return self.name

    async def str_tree(self, level=0):
        text = ["{}{}".format(level * "  ", self)]
        async for child in self.children:
            text.append(await child.str_tree(level + 1))
        return "\n".join(text)


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    root = await User.create(name="Root")
    loose = await User.create(name="Loose")
    _1 = await User.create(name="1. First H1 ", parent=root)
    _2 = await User.create(name="2. Second H1", parent=root)
    _1_1 = await User.create(name="1.1. First H2", parent=_1)
    await User.create(name="1.1.1. First H3", parent=_1_1)
    await User.create(name="2.1. Second H2", parent=_2)
    await User.create(name="2.2. Third H2", parent=_2)

    # Evaluated off creation objects
    print(await loose.str_tree())
    print(await root.str_tree())

    # Evaluated off new objects → Result is identical
    root2 = await User.get(name="Root")
    loose2 = await User.get(name="Loose")
    print(await loose2.str_tree())
    print(await root2.str_tree())


if __name__ == "__main__":
    run_async(run())
