"""
This example shows how relations between models especially unique field work.

Key points in this example are use of ForeignKeyField and OneToOneField has to_field.
For other basic parts, it is the same as relation exmaple.
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model
from tortoise.query_utils import Prefetch


class School(Model):
    uuid = fields.UUIDField(pk=True)
    name = fields.TextField()
    id = fields.IntField(unique=True)

    students: fields.ReverseRelation["Student"]
    principal: fields.ReverseRelation["Principal"]


class Student(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    school: fields.ForeignKeyRelation[School] = fields.ForeignKeyField(
        "models.School", related_name="students", to_field="id"
    )


class Principal(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    school: fields.OneToOneRelation[School] = fields.OneToOneField(
        "models.School", on_delete=fields.CASCADE, related_name="principal", to_field="id"
    )


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    school1 = await School.create(id=1024, name="School1")
    student1 = await Student.create(name="Sang-Heon Jeon1", school_id=school1.id)

    student_schools = await Student.filter(name="Sang-Heon Jeon1").values("name", "school__name")
    print(student_schools[0])

    await Student.create(name="Sang-Heon Jeon2", school=school1)
    school_with_filtered = (
        await School.all()
        .prefetch_related(Prefetch("students", queryset=Student.filter(name="Sang-Heon Jeon1")))
        .first()
    )
    school_without_filtered = await School.first().prefetch_related("students")
    print(len(school_with_filtered.students))
    print(len(school_without_filtered.students))

    school2 = await School.create(id=2048, name="School2")
    await Student.all().update(school=school2)
    student = await Student.first()
    print(student.school_id)

    await Student.filter(id=student1.id).update(school=school1)
    schools = await School.all().order_by("students__name")
    print([school.name for school in schools])

    fetched_principal = await Principal.create(name="Sang-Heon Jeon3", school=school1)
    print(fetched_principal.name)
    fetched_school = await School.filter(name="School1").prefetch_related("principal").first()
    print(fetched_school.name)


if __name__ == "__main__":
    run_async(run())
