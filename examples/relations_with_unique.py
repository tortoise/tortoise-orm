"""
This example shows how relations between models work.

Key points in this example are use of ForeignKeyField and ManyToManyField
to declare relations and use of .prefetch_related() and .fetch_related()
to get this related objects
"""
import logging

from tortoise import Tortoise, fields, run_async
from tortoise.functions import Count
from tortoise.models import Model

logging.basicConfig(level=logging.DEBUG)


class School(Model):
    uuid = fields.UUIDField(pk=True)
    name = fields.TextField()
    id = fields.IntField(unique=True)

    students: fields.ReverseRelation["Student"]


class Student(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    school: fields.ForeignKeyRelation[School] = fields.ForeignKeyField(
        "models.School", related_name="students", to_field="id"
    )


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    school = await School.create(id=1024, name="School")
    student1 = await Student.create(name="Sang-Heon Jeon1", school=school)
    student2 = await Student.create(name="Sang-Heon Jeon2", school_id=school.id)

    await School.filter(students__id=student1.id).values("id", "name", student="students__name")
    await Student.filter(id=student2.id).values("id", "name", school="school__name")
    queryset = School.all().annotate(count=Count("students"))
    await queryset.filter(name="School").first()


if __name__ == "__main__":
    run_async(run())
