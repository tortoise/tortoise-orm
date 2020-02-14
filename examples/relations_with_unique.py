"""
This example shows how relations between models work.

Key points in this example are use of ForeignKeyField and ManyToManyField
to declare relations and use of .prefetch_related() and .fetch_related()
to get this related objects
"""
import logging

from tortoise import Tortoise, fields, run_async
from tortoise.models import Model

logging.basicConfig(level=logging.DEBUG)


class School(Model):
    uuid = fields.UUIDField(pk=True)
    name = fields.TextField()
    id = fields.IntField(unique=True)

    students: fields.ReverseRelation["Student"]


class Club(Model):
    uuid = fields.UUIDField(pk=True)
    name = fields.TextField()
    club_id = fields.IntField(unique=True, source_field="club")

    students: fields.ReverseRelation["Student"]


class Student(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    school: fields.ForeignKeyRelation[School] = fields.ForeignKeyField(
        "models.School", related_name="students", to_field="id",
    )
    club: fields.ForeignKeyRelation[Club] = fields.ForeignKeyField(
        "models.Club", related_name="students", to_field="club_id",
    )


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    school = await School.create(id=1024, name="School")
    club = await Club.create(club_id=128, name="Club")
    student = await Student.create(name="Sang-Heon Jeon", school=school, club=club)
    await student.fetch_related("school", "club")
    print(student.school == school)
    print(student.club == club)
    print((await school.students.all())[0] == student)


if __name__ == "__main__":
    run_async(run())
