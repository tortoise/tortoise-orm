import os
from uuid import uuid4

import pytest
import pytest_asyncio

from tests.testmodels import (
    Dest_null,
    Event,
    IntFields,
    Node,
    NoID,
    O2O_null,
    RequiredPKModel,
    Team,
    Tournament,
    UUIDFkRelatedNullModel,
)
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ
from tortoise.exceptions import (
    ConfigurationError,
    DoesNotExist,
    IntegrityError,
    MultipleObjectsReturned,
    ObjectDoesNotExistError,
    OperationalError,
    ParamsError,
    ValidationError,
)
from tortoise.expressions import F, Q
from tortoise.models import NoneAwaitable

# ============================================================================
# TestModelCreate
# ============================================================================


@pytest.mark.asyncio
async def test_save_generated(db):
    mdl = await Tournament.create(name="Test")
    mdl2 = await Tournament.get(id=mdl.id)
    assert mdl == mdl2


@pytest.mark.asyncio
async def test_save_non_generated(db):
    mdl = await UUIDFkRelatedNullModel.create(name="Test")
    mdl2 = await UUIDFkRelatedNullModel.get(id=mdl.id)
    assert mdl == mdl2


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_save_generated_custom_id(db):
    cid = 12345
    mdl = await Tournament.create(id=cid, name="Test")
    assert mdl.id == cid
    mdl2 = await Tournament.get(id=cid)
    assert mdl == mdl2


@pytest.mark.asyncio
async def test_save_non_generated_custom_id(db):
    cid = uuid4()
    mdl = await UUIDFkRelatedNullModel.create(id=cid, name="Test")
    assert mdl.id == cid
    mdl2 = await UUIDFkRelatedNullModel.get(id=cid)
    assert mdl == mdl2


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_save_generated_duplicate_custom_id(db):
    cid = 12345
    await Tournament.create(id=cid, name="TestOriginal")
    with pytest.raises(IntegrityError):
        await Tournament.create(id=cid, name="Test")


@pytest.mark.asyncio
async def test_save_non_generated_duplicate_custom_id(db):
    cid = uuid4()
    await UUIDFkRelatedNullModel.create(id=cid, name="TestOriginal")
    with pytest.raises(IntegrityError):
        await UUIDFkRelatedNullModel.create(id=cid, name="Test")


@pytest.mark.asyncio
async def test_clone_pk_required_error(db):
    mdl = await RequiredPKModel.create(id="A", name="name_a")
    with pytest.raises(ParamsError):
        mdl.clone()


@pytest.mark.asyncio
async def test_clone_pk_required(db):
    mdl = await RequiredPKModel.create(id="A", name="name_a")
    mdl2 = mdl.clone(pk="B")
    await mdl2.save()
    mdls = list(await RequiredPKModel.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_implicit_clone_pk_required_none(db):
    mdl = await RequiredPKModel.create(id="A", name="name_a")
    mdl.pk = None
    with pytest.raises(ValidationError):
        await mdl.save()


# ============================================================================
# TestModelMethods fixtures and tests
# ============================================================================


@pytest_asyncio.fixture
async def tournament_model(db):
    """Fixture that provides a saved Tournament model instance."""
    return await Tournament.create(name="Test")


@pytest_asyncio.fixture
async def tournament_model_unsaved(db):
    """Fixture that provides an unsaved Tournament model instance."""
    return Tournament(name="Test")


@pytest.mark.asyncio
async def test_save(tournament_model):
    mdl = tournament_model
    oldid = mdl.id
    await mdl.save()
    assert mdl.id == oldid


@pytest.mark.asyncio
async def test_save_f_expression(db):
    int_field = await IntFields.create(intnum=1)
    int_field.intnum = F("intnum") + 1
    await int_field.save(update_fields=["intnum"])
    n_int = await IntFields.get(pk=int_field.pk)
    assert n_int.intnum == 2


@pytest.mark.asyncio
async def test_save_full(tournament_model):
    tournament_model.name = "TestS"
    tournament_model.desc = "Something"
    await tournament_model.save()
    n_mdl = await Tournament.get(id=tournament_model.id)
    assert n_mdl.name == "TestS"
    assert n_mdl.desc == "Something"


@pytest.mark.asyncio
async def test_save_partial(tournament_model):
    tournament_model.name = "TestS"
    tournament_model.desc = "Something"
    await tournament_model.save(update_fields=["desc"])
    n_mdl = await Tournament.get(id=tournament_model.id)
    assert n_mdl.name == "Test"
    assert n_mdl.desc == "Something"


@pytest.mark.asyncio
async def test_save_partial_with_pk_update(tournament_model):
    # Not allow to update pk field only
    with pytest.raises(OperationalError, match="Can't update pk field"):
        await tournament_model.save(update_fields=["id"])
    # So does update pk field with others
    with pytest.raises(OperationalError, match=f"use `{Tournament.__name__}.create` instead"):
        await tournament_model.save(update_fields=["id", "desc"])


@pytest.mark.asyncio
async def test_create(db):
    mdl = Tournament(name="Test2")
    assert mdl.id is None
    await mdl.save()
    assert mdl.id is not None


@pytest.mark.asyncio
async def test_delete(tournament_model, tournament_model_unsaved):
    fetched_mdl = await Tournament.get(name="Test")
    assert tournament_model.id == fetched_mdl.id

    await tournament_model.delete()

    with pytest.raises(DoesNotExist):
        await Tournament.get(name="Test")

    with pytest.raises(OperationalError):
        await tournament_model_unsaved.delete()


@pytest.mark.asyncio
async def test_str(tournament_model):
    mdl = tournament_model
    assert str(mdl) == "Test"


@pytest.mark.asyncio
async def test_repr(tournament_model, tournament_model_unsaved):
    assert repr(tournament_model) == f"<Tournament: {tournament_model.id}>"
    assert repr(tournament_model_unsaved) == "<Tournament>"


@pytest.mark.asyncio
async def test_hash(tournament_model, tournament_model_unsaved):
    assert hash(tournament_model) == tournament_model.id
    with pytest.raises(TypeError):
        hash(tournament_model_unsaved)


@pytest.mark.asyncio
async def test_eq(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.get(name="Test")
    assert mdl == fetched_mdl


@pytest.mark.asyncio
async def test_get_or_create(tournament_model):
    mdl = tournament_model
    fetched_mdl, created = await Tournament.get_or_create(name="Test")
    assert created is False
    assert mdl == fetched_mdl
    new_mdl, created = await Tournament.get_or_create(name="Test2")
    assert created is True
    assert mdl != new_mdl
    mdl2 = await Tournament.get(name="Test2")
    assert new_mdl == mdl2


@pytest.mark.asyncio
async def test_update_or_create(tournament_model):
    mdl = tournament_model
    fetched_mdl, created = await Tournament.update_or_create(name="Test")
    assert created is False
    assert mdl == fetched_mdl
    new_mdl, created = await Tournament.update_or_create(name="Test2")
    assert created is True
    assert mdl != new_mdl
    mdl2 = await Tournament.get(name="Test2")
    assert new_mdl == mdl2


@pytest.mark.asyncio
async def test_update_or_create_with_defaults(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.get(name=mdl.name)
    mdl_dict = dict(fetched_mdl)
    oldid = fetched_mdl.id
    fetched_mdl.id = 135
    with pytest.raises(ParamsError, match="Conflict value with key='id':"):
        # Missing query: check conflict with kwargs and defaults before create
        await Tournament.update_or_create(id=fetched_mdl.id, defaults=mdl_dict)
    desc = str(uuid4())
    # If there is no conflict with defaults and kwargs, it will be success to update or create
    defaults = dict(mdl_dict, desc=desc)
    kwargs = {"id": defaults["id"], "name": defaults["name"]}
    updated_mdl, created = await Tournament.update_or_create(defaults, **kwargs)
    assert created is False
    assert defaults["desc"] == updated_mdl.desc
    assert mdl.desc != updated_mdl.desc
    # Hint query: use defauts to update without checking conflict
    mdl2, created = await Tournament.update_or_create(
        id=oldid, desc=desc, defaults=dict(mdl_dict, desc="new desc")
    )
    assert created is False
    assert dict(updated_mdl) != dict(mdl2)
    # Missing query: success to create if no conflict
    not_exist_name = str(uuid4())
    no_conflict_defaults = {"name": not_exist_name, "desc": desc}
    no_conflict_kwargs = {"name": not_exist_name}
    created_mdl, created = await Tournament.update_or_create(
        no_conflict_defaults, **no_conflict_kwargs
    )
    assert created is True
    assert not_exist_name == created_mdl.name


@pytest.mark.asyncio
async def test_first(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.first()
    assert mdl.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_last(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.last()
    assert mdl.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_latest(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.latest("name")
    assert mdl.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_earliest(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.earliest("name")
    assert mdl.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_filter(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.filter(name="Test").first()
    assert mdl.id == fetched_mdl.id
    fetched_mdl = await Tournament.filter(name="Test2").first()
    assert fetched_mdl is None


@pytest.mark.asyncio
async def test_all(tournament_model):
    mdl = tournament_model
    mdls = list(await Tournament.all())
    assert len(mdls) == 1
    assert mdls == [mdl]


@pytest.mark.asyncio
async def test_get(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.get(name="Test")
    assert mdl.id == fetched_mdl.id

    with pytest.raises(DoesNotExist):
        await Tournament.get(name="Test2")

    await Tournament.create(name="Test")

    with pytest.raises(MultipleObjectsReturned):
        await Tournament.get(name="Test")


@pytest.mark.asyncio
async def test_exists(db):
    await Tournament.create(name="Test")
    ret = await Tournament.exists(name="Test")
    assert ret is True

    ret = await Tournament.exists(name="XXX")
    assert ret is False

    ret = await Tournament.exists(Q(name="XXX") & Q(name="Test"))
    assert ret is False


@pytest.mark.asyncio
async def test_get_or_none(tournament_model):
    mdl = tournament_model
    fetched_mdl = await Tournament.get_or_none(name="Test")
    assert mdl.id == fetched_mdl.id

    fetched_mdl = await Tournament.get_or_none(name="Test2")
    assert fetched_mdl is None

    await Tournament.create(name="Test")

    with pytest.raises(MultipleObjectsReturned):
        await Tournament.get_or_none(name="Test")


@pytest.mark.skipif(os.name == "nt", reason="timestamp issue on Windows")
@pytest.mark.asyncio
async def test_update_from_dict(db):
    evt1 = await Event.create(name="a", tournament=await Tournament.create(name="a"))
    orig_modified = evt1.modified
    await evt1.update_from_dict({"alias": "8", "name": "b", "bad_name": "foo"}).save()
    assert evt1.alias == 8
    assert evt1.name == "b"

    with pytest.raises(AttributeError):
        _ = evt1.bad_name

    evt2 = await Event.get(name="b")
    assert evt1.pk == evt2.pk
    assert evt1.modified == evt2.modified
    assert orig_modified != evt1.modified

    with pytest.raises(ConfigurationError):
        await evt2.update_from_dict({"participants": []})

    with pytest.raises(ValueError):
        await evt2.update_from_dict({"alias": "foo"})


@pytest.mark.asyncio
async def test_index_access(tournament_model):
    obj = await Tournament[tournament_model.pk]
    assert obj == tournament_model


@pytest.mark.asyncio
async def test_index_badval(db):
    with pytest.raises(ObjectDoesNotExistError) as exc_info:
        await Tournament[32767]
    the_exception = exc_info.value
    # For compatibility reasons this should be an instance of KeyError
    assert isinstance(the_exception, KeyError)
    assert the_exception.model is Tournament
    assert the_exception.pk_name == "id"
    assert the_exception.pk_val == 32767
    assert str(the_exception) == f"{Tournament.__name__} has no object with id=32767"


@pytest.mark.asyncio
async def test_index_badtype(db):
    with pytest.raises(ObjectDoesNotExistError) as exc_info:
        await Tournament["asdf"]
    the_exception = exc_info.value
    # For compatibility reasons this should be an instance of KeyError
    assert isinstance(the_exception, KeyError)
    assert the_exception.model is Tournament
    assert the_exception.pk_name == "id"
    assert the_exception.pk_val == "asdf"
    assert str(the_exception) == f"{Tournament.__name__} has no object with id=asdf"


@pytest.mark.asyncio
async def test_clone(tournament_model):
    mdl = tournament_model
    mdl2 = mdl.clone()
    assert mdl2.pk is None
    await mdl2.save()
    assert mdl2.pk != mdl.pk
    mdls = list(await Tournament.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_clone_with_pk(tournament_model):
    mdl = tournament_model
    mdl2 = mdl.clone(pk=8888)
    assert mdl2.pk == 8888
    await mdl2.save()
    assert mdl2.pk != mdl.pk
    await mdl2.save()
    mdls = list(await Tournament.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_clone_from_db(tournament_model):
    mdl = tournament_model
    mdl2 = await Tournament.get(pk=mdl.pk)
    mdl3 = mdl2.clone()
    mdl3.pk = None
    await mdl3.save()
    assert mdl3.pk != mdl2.pk
    mdls = list(await Tournament.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_implicit_clone(tournament_model):
    mdl = tournament_model
    mdl.pk = None
    await mdl.save()
    mdls = list(await Tournament.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_force_create(tournament_model):
    obj = Tournament(name="Test", id=tournament_model.id)
    with pytest.raises(IntegrityError):
        await obj.save(force_create=True)


@pytest.mark.asyncio
async def test_force_update(tournament_model):
    obj = Tournament(name="Test3", id=tournament_model.id)
    await obj.save(force_update=True)


@pytest.mark.asyncio
async def test_force_update_raise(tournament_model):
    obj = Tournament(name="Test3", id=tournament_model.id + 100)
    with pytest.raises(IntegrityError):
        await obj.save(force_update=True)


@pytest.mark.asyncio
async def test_raw(db):
    await Node.create(name="TestRaw")
    ret = await Node.raw("select * from node where name='TestRaw'")
    assert len(ret) == 1
    ret = await Node.raw("select * from node where name='111'")
    assert len(ret) == 0


# ============================================================================
# TestModelMethodsNoID fixtures and tests
# ============================================================================


@pytest_asyncio.fixture
async def noid_model(db):
    """Fixture that provides a saved NoID model instance."""
    return await NoID.create(name="Test")


@pytest_asyncio.fixture
async def noid_model_unsaved(db):
    """Fixture that provides an unsaved NoID model instance."""
    return NoID(name="Test")


@pytest.mark.asyncio
async def test_noid_save(noid_model):
    oldid = noid_model.id
    await noid_model.save()
    assert noid_model.id == oldid


@pytest.mark.asyncio
async def test_noid_save_f_expression(db):
    int_field = await IntFields.create(intnum=1)
    int_field.intnum = F("intnum") + 1
    await int_field.save(update_fields=["intnum"])
    n_int = await IntFields.get(pk=int_field.pk)
    assert n_int.intnum == 2


@pytest.mark.asyncio
async def test_noid_save_full(noid_model):
    noid_model.name = "TestS"
    await noid_model.save()
    n_mdl = await NoID.get(id=noid_model.id)
    assert n_mdl.name == "TestS"


@pytest.mark.asyncio
async def test_noid_save_partial(noid_model):
    noid_model.name = "TestS"
    noid_model.desc = "Something"
    await noid_model.save(update_fields=["desc"])
    n_mdl = await NoID.get(id=noid_model.id)
    assert n_mdl.name == "Test"  # name should not be updated
    assert n_mdl.desc == "Something"  # desc should be updated


@pytest.mark.asyncio
async def test_noid_save_partial_with_pk_update(noid_model):
    # Not allow to update pk field only
    with pytest.raises(OperationalError, match="Can't update pk field"):
        await noid_model.save(update_fields=["id"])
    # So does update pk field with others
    with pytest.raises(OperationalError, match=f"use `{NoID.__name__}.create` instead"):
        await noid_model.save(update_fields=["id", "name"])


@pytest.mark.asyncio
async def test_noid_create(db):
    mdl = NoID(name="Test2")
    assert mdl.id is None
    await mdl.save()
    assert mdl.id is not None


@pytest.mark.asyncio
async def test_noid_delete(noid_model, noid_model_unsaved):
    fetched_mdl = await NoID.get(name="Test")
    assert noid_model.id == fetched_mdl.id

    await noid_model.delete()

    with pytest.raises(DoesNotExist):
        await NoID.get(name="Test")

    with pytest.raises(OperationalError):
        await noid_model_unsaved.delete()


@pytest.mark.asyncio
async def test_noid_str(noid_model):
    assert str(noid_model) == "<NoID>"


@pytest.mark.asyncio
async def test_noid_repr(noid_model, noid_model_unsaved):
    assert repr(noid_model) == f"<NoID: {noid_model.id}>"
    assert repr(noid_model_unsaved) == "<NoID>"


@pytest.mark.asyncio
async def test_noid_hash(noid_model, noid_model_unsaved):
    assert hash(noid_model) == noid_model.id
    with pytest.raises(TypeError):
        hash(noid_model_unsaved)


@pytest.mark.asyncio
async def test_noid_eq(noid_model):
    fetched_mdl = await NoID.get(name="Test")
    assert noid_model == fetched_mdl


@pytest.mark.asyncio
async def test_noid_get_or_create(noid_model):
    fetched_mdl, created = await NoID.get_or_create(name="Test")
    assert created is False
    assert noid_model == fetched_mdl
    new_mdl, created = await NoID.get_or_create(name="Test2")
    assert created is True
    assert noid_model != new_mdl
    mdl2 = await NoID.get(name="Test2")
    assert new_mdl == mdl2


@pytest.mark.asyncio
async def test_noid_update_or_create(noid_model):
    fetched_mdl, created = await NoID.update_or_create(name="Test")
    assert created is False
    assert noid_model == fetched_mdl
    new_mdl, created = await NoID.update_or_create(name="Test2")
    assert created is True
    assert noid_model != new_mdl
    mdl2 = await NoID.get(name="Test2")
    assert new_mdl == mdl2


@pytest.mark.asyncio
async def test_noid_first(noid_model):
    fetched_mdl = await NoID.first()
    assert noid_model.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_noid_last(noid_model):
    fetched_mdl = await NoID.last()
    assert noid_model.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_noid_latest(noid_model):
    fetched_mdl = await NoID.latest("name")
    assert noid_model.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_noid_earliest(noid_model):
    fetched_mdl = await NoID.earliest("name")
    assert noid_model.id == fetched_mdl.id


@pytest.mark.asyncio
async def test_noid_filter(noid_model):
    fetched_mdl = await NoID.filter(name="Test").first()
    assert noid_model.id == fetched_mdl.id
    fetched_mdl = await NoID.filter(name="Test2").first()
    assert fetched_mdl is None


@pytest.mark.asyncio
async def test_noid_all(noid_model):
    mdls = list(await NoID.all())
    assert len(mdls) == 1
    assert mdls == [noid_model]


@pytest.mark.asyncio
async def test_noid_get(noid_model):
    fetched_mdl = await NoID.get(name="Test")
    assert noid_model.id == fetched_mdl.id

    with pytest.raises(DoesNotExist):
        await NoID.get(name="Test2")

    await NoID.create(name="Test")

    with pytest.raises(MultipleObjectsReturned):
        await NoID.get(name="Test")


@pytest.mark.asyncio
async def test_noid_exists(noid_model):
    await NoID.create(name="Test")
    ret = await NoID.exists(name="Test")
    assert ret is True

    ret = await NoID.exists(name="XXX")
    assert ret is False

    ret = await NoID.exists(Q(name="XXX") & Q(name="Test"))
    assert ret is False


@pytest.mark.asyncio
async def test_noid_get_or_none(noid_model):
    fetched_mdl = await NoID.get_or_none(name="Test")
    assert noid_model.id == fetched_mdl.id

    fetched_mdl = await NoID.get_or_none(name="Test2")
    assert fetched_mdl is None

    await NoID.create(name="Test")

    with pytest.raises(MultipleObjectsReturned):
        await NoID.get_or_none(name="Test")


@pytest.mark.asyncio
async def test_noid_index_access(noid_model):
    obj = await NoID[noid_model.pk]
    assert obj == noid_model


@pytest.mark.asyncio
async def test_noid_index_badval(db):
    with pytest.raises(ObjectDoesNotExistError) as exc_info:
        await NoID[32767]
    the_exception = exc_info.value
    # For compatibility reasons this should be an instance of KeyError
    assert isinstance(the_exception, KeyError)
    assert the_exception.model is NoID
    assert the_exception.pk_name == "id"
    assert the_exception.pk_val == 32767
    assert str(the_exception) == f"{NoID.__name__} has no object with id=32767"


@pytest.mark.asyncio
async def test_noid_index_badtype(db):
    with pytest.raises(ObjectDoesNotExistError) as exc_info:
        await NoID["asdf"]
    the_exception = exc_info.value
    # For compatibility reasons this should be an instance of KeyError
    assert isinstance(the_exception, KeyError)
    assert the_exception.model is NoID
    assert the_exception.pk_name == "id"
    assert the_exception.pk_val == "asdf"
    assert str(the_exception) == f"{NoID.__name__} has no object with id=asdf"


@pytest.mark.asyncio
async def test_noid_clone(noid_model):
    mdl2 = noid_model.clone()
    assert mdl2.pk is None
    await mdl2.save()
    assert mdl2.pk != noid_model.pk
    mdls = list(await NoID.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_noid_clone_with_pk(noid_model):
    mdl2 = noid_model.clone(pk=8888)
    assert mdl2.pk == 8888
    await mdl2.save()
    assert mdl2.pk != noid_model.pk
    await mdl2.save()
    mdls = list(await NoID.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_noid_clone_from_db(noid_model):
    mdl2 = await NoID.get(pk=noid_model.pk)
    mdl3 = mdl2.clone()
    mdl3.pk = None
    await mdl3.save()
    assert mdl3.pk != mdl2.pk
    mdls = list(await NoID.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_noid_implicit_clone(noid_model):
    noid_model.pk = None
    await noid_model.save()
    mdls = list(await NoID.all())
    assert len(mdls) == 2


@pytest.mark.asyncio
async def test_noid_force_create(noid_model):
    obj = NoID(name="Test", id=noid_model.id)
    with pytest.raises(IntegrityError):
        await obj.save(force_create=True)


@pytest.mark.asyncio
async def test_noid_force_update(noid_model):
    obj = NoID(name="Test3", id=noid_model.id)
    await obj.save(force_update=True)


@pytest.mark.asyncio
async def test_noid_force_update_raise(noid_model):
    obj = NoID(name="Test3", id=noid_model.id + 100)
    with pytest.raises(IntegrityError):
        await obj.save(force_update=True)


# ============================================================================
# TestModelConstructor
# ============================================================================


def test_null_in_nonnull_field():
    with pytest.raises(ValueError, match="name is non nullable field, but null was passed"):
        Event(name=None)


def test_rev_fk():
    with pytest.raises(
        ConfigurationError,
        match="You can't set backward relations through init, change related model instead",
    ):
        Tournament(name="a", events=[])


def test_m2m():
    with pytest.raises(
        ConfigurationError,
        match="You can't set m2m relations through init, use m2m_manager instead",
    ):
        Event(name="a", participants=[])


def test_rev_m2m():
    with pytest.raises(
        ConfigurationError,
        match="You can't set m2m relations through init, use m2m_manager instead",
    ):
        Team(name="a", events=[])


@pytest.mark.asyncio
async def test_rev_o2o(db):
    with pytest.raises(
        ConfigurationError,
        match="You can't set backward one to one relations through init, "
        "change related model instead",
    ):
        address = await O2O_null.create(name="Ocean")
        await Dest_null(name="a", address_null=address)


def test_fk_unsaved():
    with pytest.raises(OperationalError, match="You should first call .save()"):
        Event(name="a", tournament=Tournament(name="a"))


@pytest.mark.asyncio
async def test_fk_saved(db):
    await Event.create(name="a", tournament=await Tournament.create(name="a"))


@pytest.mark.asyncio
async def test_noneawaitable(db):
    assert not NoneAwaitable
    assert await NoneAwaitable is None
    assert not NoneAwaitable
    assert await NoneAwaitable is None
