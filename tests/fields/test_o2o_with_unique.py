from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError, OperationalError
from tortoise.queryset import QuerySet


class TestOneToOneFieldWithUnique(test.TestCase):
    async def test_principal__empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.Principal.create()

    async def test_principal__create_by_id(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school_id=school.id)
        self.assertEqual(principal.school_id, school.id)
        self.assertEqual(await school.principal, principal)

    async def test_principal__create_by_name(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
        await principal.fetch_related("school")
        self.assertEqual(principal.school, school)
        self.assertEqual(await school.principal, principal)

    async def test_principal__by_name__created_prefetched(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
        self.assertEqual(principal.school, school)
        self.assertEqual(await school.principal, principal)

    async def test_principal__by_name__unfetched(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
        principal = await testmodels.Principal.get(id=principal.id)
        self.assertIsInstance(principal.school, QuerySet)

    async def test_principal__by_name__re_awaited(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
        await principal.fetch_related("school")
        self.assertEqual(principal.school, school)
        self.assertEqual(await principal.school, school)

    async def test_principal__by_name__awaited(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
        principal = await testmodels.Principal.get(id=principal.id)
        self.assertEqual(await principal.school, school)
        self.assertEqual(await school.principal, principal)

    async def test_update_by_name(self):
        school = await testmodels.School.create(id=1024, name="School1")
        school2 = await testmodels.School.create(id=2048, name="School2")
        principal0 = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)

        await testmodels.Principal.filter(id=principal0.id).update(school=school2)
        principal = await testmodels.Principal.get(id=principal0.id)

        await principal.fetch_related("school")
        self.assertEqual(principal.school, school2)
        self.assertEqual(await school.principal, None)
        self.assertEqual(await school2.principal, principal)

    async def test_update_by_id(self):
        school = await testmodels.School.create(id=1024, name="School1")
        school2 = await testmodels.School.create(id=2048, name="School2")
        principal0 = await testmodels.Principal.create(name="Sang-Heon Jeon", school_id=school.id)

        await testmodels.Principal.filter(id=principal0.id).update(school_id=school2.id)
        principal = await testmodels.Principal.get(id=principal0.id)

        self.assertEqual(principal.school_id, school2.id)
        self.assertEqual(await school.principal, None)
        self.assertEqual(await school2.principal, principal)

    async def test_delete_by_name(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
        del principal.school
        with self.assertRaises(IntegrityError):
            await principal.save()

    async def test_principal__uninstantiated_create(self):
        school = await testmodels.School(id=1024, name="School1")
        with self.assertRaisesRegex(OperationalError, "You should first call .save()"):
            await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)

    async def test_principal__instantiated_create(self):
        school = await testmodels.School.create(id=1024, name="School1")
        await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)

    async def test_principal__fetched_bool(self):
        school = await testmodels.School.create(id=1024, name="School1")
        await school.fetch_related("principal")
        self.assertFalse(bool(school.principal))
        await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
        await school.fetch_related("principal")
        self.assertTrue(bool(school.principal))

    async def test_principal__filter(self):
        school = await testmodels.School.create(id=1024, name="School1")
        principal = await testmodels.Principal.create(name="Sang-Heon Jeon1", school=school)
        self.assertEqual(await school.principal.filter(name="Sang-Heon Jeon1"), principal)
        self.assertEqual(await school.principal.filter(name="Sang-Heon Jeon2"), None)
