from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import NoValuesFetched, OperationalError
from tortoise.queryset import QuerySet


class TestForeignKeyFieldWithUnique(test.TestCase):
    async def test_student__create_by_id(self):
        school = await testmodels.School.create(id=1024, name="School1")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school_id=school.id)
        self.assertEqual(student.school_id, school.id)
        self.assertEqual((await school.students.all())[0], student)

    async def test_student__create_by_name(self):
        school = await testmodels.School.create(id=1024, name="School1")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        await student.fetch_related("school")
        self.assertEqual(student.school, school)
        self.assertEqual((await school.students.all())[0], student)

    async def test_student__by_name__created_prefetched(self):
        school = await testmodels.School.create(id=1024, name="School1")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        self.assertEqual(student.school, school)
        self.assertEqual((await school.students.all())[0], student)

    async def test_student__by_name__unfetched(self):
        school = await testmodels.School.create(id=1024, name="School1")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        student = await testmodels.Student.get(id=student.id)
        self.assertIsInstance(student.school, QuerySet)

    async def test_student__by_name__re_awaited(self):
        school = await testmodels.School.create(id=1024, name="School1")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        await student.fetch_related("school")
        self.assertEqual(student.school, school)
        self.assertEqual(await student.school, school)

    async def test_student__by_name__awaited(self):
        school = await testmodels.School.create(id=1024, name="School1")
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

    async def test_student__uninstantiated_create(self):
        school = await testmodels.School(id=1024, name="School1")
        with self.assertRaisesRegex(OperationalError, "You should first call .save()"):
            await testmodels.Student.create(name="Sang-Heon Jeon", school=school)

    async def test_student__uninstantiated_iterate(self):
        school = await testmodels.School(id=1024, name="School1")
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            async for _ in school.students:
                pass

    async def test_student__uninstantiated_await(self):
        school = await testmodels.School(id=1024, name="School1")
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            await school.students

    async def test_student__unfetched_contains(self):
        school = await testmodels.School.create(id=1024, name="School1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            "a" in school.students  # pylint: disable=W0104

    async def test_stduent__unfetched_iter(self):
        school = await testmodels.School.create(id=1024, name="School1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            for _ in school.students:
                pass

    async def test_student__unfetched_len(self):
        school = await testmodels.School.create(id=1024, name="School1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            len(school.students)

    async def test_student__unfetched_bool(self):
        school = await testmodels.School.create(id=1024, name="School1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            bool(school.students)

    async def test_student__unfetched_getitem(self):
        school = await testmodels.School.create(id=1024, name="School1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            school.students[0]  # pylint: disable=W0104

    async def test_student__instantiated_create(self):
        school = await testmodels.School.create(id=1024, name="School1")
        await testmodels.Student.create(name="Sang-Heon Jeon", school=school)

    async def test_student__instantiated_iterate(self):
        school = await testmodels.School.create(id=1024, name="School1")
        async for _ in school.students:
            pass

    async def test_student__instantiated_await(self):
        school = await testmodels.School.create(id=1024, name="School1")
        await school.students

    async def test_student__fetched_contains(self):
        school = await testmodels.School.create(id=1024, name="School1")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        await school.fetch_related("students")
        self.assertTrue(student in school.students)

    async def test_student__fetched_iter(self):
        school = await testmodels.School.create(id=1024, name="School1")
        student = await testmodels.Student.create(name="Sang-Heon Jeon", school=school)
        await school.fetch_related("students")
        self.assertEqual(list(school.students), [student])
