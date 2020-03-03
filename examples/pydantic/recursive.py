"""
This example demonstrates pydantic serialisation of a recursively cycled model.
"""
from tortoise import Tortoise, fields, run_async
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import NoValuesFetched
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

    def name_length(self) -> int:
        # Computes length of name
        # Note that this function needs to be annotated with a return type so that pydantic
        # can generate a valid schema
        return len(self.name)

    def team_size(self) -> int:
        """
        Computes team size.

        Note that this function needs to be annotated with a return type so that pydantic can
         generate a valid schema.

        Note that the pydantic serializer can't call async methods, but the tortoise helpers
         pre-fetch relational data, so that it is available before serialization. So we don't
         need to await the relation. We do however have to protect against the case where no
         prefetching was done, hence catching and handling the
         ``tortoise.exceptions.NoValuesFetched`` exception.
        """
        try:
            return len(self.team_members)
        except NoValuesFetched:
            return -1

    def not_annotated(self):
        # Never called due to no annotation!
        raise NotImplementedError("Not Done")

    class PydanticMeta:
        computed = ["name_length", "team_size", "not_annotated"]
        exclude = ["manager", "gets_talked_to"]
        allow_cycles = True
        max_recursion = 4


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    Employee_Pydantic = pydantic_model_creator(Employee)
    # print(Employee_Pydantic.schema_json(indent=4))

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

    p = await Employee_Pydantic.from_tortoise_orm(await Employee.get(name="Root"))
    print(p.json(indent=4))


if __name__ == "__main__":
    run_async(run())
