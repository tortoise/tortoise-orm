from tests.testmodels import Principal, School, Student
from tortoise.contrib import test
from tortoise.query_utils import Prefetch


class TestRelationsWithUnique(test.TestCase):
    async def test_relation_with_unique(self):
        school1 = await School.create(id=1024, name="School1")
        student1 = await Student.create(name="Sang-Heon Jeon1", school_id=school1.id)

        student_schools = await Student.filter(name="Sang-Heon Jeon1").values(
            "name", "school__name"
        )
        self.assertEqual(student_schools[0], {"name": "Sang-Heon Jeon1", "school__name": "School1"})
        student_schools = await Student.all().values(school="school__name")
        self.assertEqual(student_schools[0]["school"], school1.name)
        student_schools = await Student.all().values_list("school__name")
        self.assertEqual(student_schools[0][0], school1.name)

        await Student.create(name="Sang-Heon Jeon2", school=school1)
        school_with_filtered = (
            await School.all()
            .prefetch_related(Prefetch("students", queryset=Student.filter(name="Sang-Heon Jeon1")))
            .first()
        )
        school_without_filtered = await School.first().prefetch_related("students")
        self.assertEqual(len(school_with_filtered.students), 1)
        self.assertEqual(len(school_without_filtered.students), 2)

        student_direct_prefetch = await Student.first().prefetch_related("school")
        self.assertEqual(student_direct_prefetch.school.id, school1.id)

        school2 = await School.create(id=2048, name="School2")
        await Student.all().update(school=school2)
        student = await Student.first()
        self.assertEqual(student.school_id, school2.id)

        await Student.filter(id=student1.id).update(school=school1)
        schools = await School.all().order_by("students__name")
        self.assertEqual([school.name for school in schools], ["School1", "School2"])
        schools = await School.all().order_by("-students__name")
        self.assertEqual([school.name for school in schools], ["School2", "School1"])

        fetched_principal = await Principal.create(name="Sang-Heon Jeon3", school=school1)
        self.assertEqual(fetched_principal.name, "Sang-Heon Jeon3")
        fetched_school = await School.filter(name="School1").prefetch_related("principal").first()
        self.assertEqual(fetched_school.name, "School1")
