from tests import testmodels
from tortoise.contrib import test
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

    async def test_update_by_name(self):
        school = await testmodels.School.create(id=1024, name="School1")
        school2 = await testmodels.School.create(id=2048, name="School2")
        student0 = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)

        await testmodels.Student.filter(id=student0.id).update(school=school2)
        student = await testmodels.Student.get(id=student0.id)

        await student.fetch_related("school")
        self.assertEqual(student.school, school2)
        self.assertEqual(await school.students.all(), [])
        self.assertEqual((await school2.students.all())[0], student)

    async def test_update_by_id(self):
        school = await testmodels.School.create(id=1024, name="School1")
        school2 = await testmodels.School.create(id=2048, name="School2")
        student0 = await testmodels.Student.create(name="Sang-Heon Jeon", school_id=school.id)

        await testmodels.Student.filter(id=student0.id).update(school_id=school2.id)
        student = await testmodels.Student.get(id=student0.id)

        self.assertEqual(student.school_id, school2.id)
        self.assertEqual(await school.students.all(), [])
        self.assertEqual((await school2.students.all())[0], student)
