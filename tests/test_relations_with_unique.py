from tests.testmodels import School, Student
from tortoise.contrib import test


class TestRelationsWithUnique(test.TestCase):
    async def test_relation_with_unique(self):
        school = await School.create(id=1024, name="School")
        await Student.create(name="Sang-Heon Jeon", school_id=school.id)

        student_schools = await Student.all().values(school="school__name")
        self.assertEqual(student_schools[0]["school"], school.name)
        student_schools = await Student.all().values_list("school__name")
        self.assertEqual(student_schools[0][0], school.name)
