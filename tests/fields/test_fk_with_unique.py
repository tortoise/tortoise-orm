from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError, NoValuesFetched, OperationalError
from tortoise.queryset import QuerySet


class TestForeignKeyFieldWithUnique(test.TestCase):
    async def test_student__create_by_id(self):
        school = await testmodels.School.create(id=1024, name="School")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school_id=school.id)
        self.assertEqual(student.school_id, school.id)
        self.assertEqual((await school.students.all())[0], student)

    async def test_student__create_by_name(self):
        school = await testmodels.School.create(id=1024, name="School")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        await student.fetch_related("school")
        self.assertEqual(student.school, school)
        self.assertEqual((await school.students.all())[0], student)

    async def test_student__by_name__created_prefetched(self):
        school = await testmodels.School.create(id=1024, name="School")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        self.assertEqual(student.school, school)
        self.assertEqual((await school.students.all())[0], student)

    async def test_student__by_name__unfetched(self):
        school = await testmodels.School.create(id=1024, name="School")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        student = await testmodels.Student.get(id=student.id)
        self.assertIsInstance(student.school, QuerySet)

    async def test_student__by_name__re_awaited(self):
        school = await testmodels.School.create(id=1024, name="School")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        await student.fetch_related("school")
        self.assertEqual(student.school, school)
        self.assertEqual(await student.school, school)

    async def test_student__by_name__awaited(self):
        school = await testmodels.School.create(id=1024, name="School")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        student = await testmodels.Student.get(id=student.id)
        self.assertEqual(await student.school, school)
        self.assertEqual((await school.students.all())[0], student)
