import pytest

from tests import testmodels
from tortoise.exceptions import IntegrityError, OperationalError
from tortoise.queryset import QuerySet


@pytest.mark.asyncio
async def test_principal__empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.Principal.create()


@pytest.mark.asyncio
async def test_principal__create_by_id(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school_id=school.id)
    assert principal.school_id == school.id
    assert await school.principal == principal


@pytest.mark.asyncio
async def test_principal__create_by_name(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
    await principal.fetch_related("school")
    assert principal.school == school
    assert await school.principal == principal


@pytest.mark.asyncio
async def test_principal__by_name__created_prefetched(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
    assert principal.school == school
    assert await school.principal == principal


@pytest.mark.asyncio
async def test_principal__by_name__unfetched(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
    principal = await testmodels.Principal.get(id=principal.id)
    assert isinstance(principal.school, QuerySet)


@pytest.mark.asyncio
async def test_principal__by_name__re_awaited(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
    await principal.fetch_related("school")
    assert principal.school == school
    assert await principal.school == school


@pytest.mark.asyncio
async def test_principal__by_name__awaited(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
    principal = await testmodels.Principal.get(id=principal.id)
    assert await principal.school == school
    assert await school.principal == principal


@pytest.mark.asyncio
async def test_update_by_name(db):
    school = await testmodels.School.create(id=1024, name="School1")
    school2 = await testmodels.School.create(id=2048, name="School2")
    principal0 = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)

    await testmodels.Principal.filter(id=principal0.id).update(school=school2)
    principal = await testmodels.Principal.get(id=principal0.id)

    await principal.fetch_related("school")
    assert principal.school == school2
    assert await school.principal is None
    assert await school2.principal == principal


@pytest.mark.asyncio
async def test_update_by_id(db):
    school = await testmodels.School.create(id=1024, name="School1")
    school2 = await testmodels.School.create(id=2048, name="School2")
    principal0 = await testmodels.Principal.create(name="Sang-Heon Jeon", school_id=school.id)

    await testmodels.Principal.filter(id=principal0.id).update(school_id=school2.id)
    principal = await testmodels.Principal.get(id=principal0.id)

    assert principal.school_id == school2.id
    assert await school.principal is None
    assert await school2.principal == principal


@pytest.mark.asyncio
async def test_delete_by_name(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
    del principal.school
    with pytest.raises(IntegrityError):
        await principal.save()


@pytest.mark.asyncio
async def test_principal__uninstantiated_create(db):
    school = await testmodels.School(id=1024, name="School1")
    with pytest.raises(OperationalError, match="You should first call .save()"):
        await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)


@pytest.mark.asyncio
async def test_principal__instantiated_create(db):
    school = await testmodels.School.create(id=1024, name="School1")
    await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)


@pytest.mark.asyncio
async def test_principal__fetched_bool(db):
    school = await testmodels.School.create(id=1024, name="School1")
    await school.fetch_related("principal")
    assert not bool(school.principal)
    await testmodels.Principal.create(name="Sang-Heon Jeon", school=school)
    await school.fetch_related("principal")
    assert bool(school.principal)


@pytest.mark.asyncio
async def test_principal__filter(db):
    school = await testmodels.School.create(id=1024, name="School1")
    principal = await testmodels.Principal.create(name="Sang-Heon Jeon1", school=school)
    assert await school.principal.filter(name="Sang-Heon Jeon1") == principal
    assert await school.principal.filter(name="Sang-Heon Jeon2") is None
