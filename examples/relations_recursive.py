"""
This example shows how self-referential (recursive) relations work.

Key points in this example are:
* Use of ForeignKeyField that refers to self
* To pass in the (optional) parent node at creation
* To use async iterator to fetch children
* To use .fetch_related(…) to emulate sync behaviour
* That insert-order gets preserved for ForeignFields, but not ManyToManyFields
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model


class Employee(Model):
    name = fields.CharField(max_length=50)

    manager: fields.ForeignKeyNullableRelation["Employee"] = fields.ForeignKeyField(
        "models.Employee", related_name="team_members", null=True
    )
    team_members: fields.ReverseRelation["Employee"]

    talks_to: fields.ManyToManyRelation["Employee"] = fields.ManyToManyField(
        "models.Employee", related_name="gets_talked_to"
    )
    gets_talked_to: fields.ManyToManyRelation["Employee"]

    def __str__(self):
        return self.name

    async def full_hierarchy__async_for(self, level=0):
        """
        Demonstrates ``async for` to fetch relations

        An async iterator will fetch the relationship on-demand.
        """
        text = [
            "{}{} (to: {}) (from: {})".format(
                level * "  ",
                self,
                ", ".join([str(val) async for val in self.talks_to]),
                ", ".join([str(val) async for val in self.gets_talked_to]),
            )
        ]
        async for member in self.team_members:
            text.append(await member.full_hierarchy__async_for(level + 1))
        return "\n".join(text)

    async def full_hierarchy__fetch_related(self, level=0):
        """
        Demonstrates ``await .fetch_related`` to fetch relations

        On prefetching the data, the relationship files will contain a regular list.

        This is how one would get relations working on sync serialization/templating frameworks.
        """
        await self.fetch_related("team_members", "talks_to", "gets_talked_to")
        text = [
            "{}{} (to: {}) (from: {})".format(
                level * "  ",
                self,
                ", ".join([str(val) for val in self.talks_to]),
                ", ".join([str(val) for val in self.gets_talked_to]),
            )
        ]
        for member in self.team_members:
            text.append(await member.full_hierarchy__fetch_related(level + 1))
        return "\n".join(text)


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    root = await Employee.create(name="Root")
    loose = await Employee.create(name="Loose")
    _1 = await Employee.create(name="1. First H1", manager=root)
    _2 = await Employee.create(name="2. Second H1", manager=root)
    _1_1 = await Employee.create(name="1.1. First H2", manager=_1)
    _1_1_1 = await Employee.create(name="1.1.1. First H3", manager=_1_1)
    _2_1 = await Employee.create(name="2.1. Second H2", manager=_2)
    _2_2 = await Employee.create(name="2.2. Third H2", manager=_2)

    await _1.talks_to.add(_2, _1_1_1, loose)
    await _2_1.gets_talked_to.add(_2_2, _1_1, loose)

    # Evaluated off creation objects
    print(await loose.full_hierarchy__fetch_related())
    print(await root.full_hierarchy__async_for())
    print(await root.full_hierarchy__fetch_related())

    # Evaluated off new objects → Result is identical
    root2 = await Employee.get(name="Root")
    loose2 = await Employee.get(name="Loose")
    print(await loose2.full_hierarchy__fetch_related())
    print(await root2.full_hierarchy__async_for())
    print(await root2.full_hierarchy__fetch_related())


if __name__ == "__main__":
    run_async(run())
