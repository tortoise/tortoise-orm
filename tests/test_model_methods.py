import os
from uuid import uuid4

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
from tortoise.contrib import test
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


class TestModelCreate(test.TestCase):
    async def test_save_generated(self):
        mdl = await Tournament.create(name="Test")
        mdl2 = await Tournament.get(id=mdl.id)
        self.assertEqual(mdl, mdl2)

    async def test_save_non_generated(self):
        mdl = await UUIDFkRelatedNullModel.create(name="Test")
        mdl2 = await UUIDFkRelatedNullModel.get(id=mdl.id)
        self.assertEqual(mdl, mdl2)

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_save_generated_custom_id(self):
        cid = 12345
        mdl = await Tournament.create(id=cid, name="Test")
        self.assertEqual(mdl.id, cid)
        mdl2 = await Tournament.get(id=cid)
        self.assertEqual(mdl, mdl2)

    async def test_save_non_generated_custom_id(self):
        cid = uuid4()
        mdl = await UUIDFkRelatedNullModel.create(id=cid, name="Test")
        self.assertEqual(mdl.id, cid)
        mdl2 = await UUIDFkRelatedNullModel.get(id=cid)
        self.assertEqual(mdl, mdl2)

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_save_generated_duplicate_custom_id(self):
        cid = 12345
        await Tournament.create(id=cid, name="TestOriginal")
        with self.assertRaises(IntegrityError):
            await Tournament.create(id=cid, name="Test")

    async def test_save_non_generated_duplicate_custom_id(self):
        cid = uuid4()
        await UUIDFkRelatedNullModel.create(id=cid, name="TestOriginal")
        with self.assertRaises(IntegrityError):
            await UUIDFkRelatedNullModel.create(id=cid, name="Test")

    async def test_clone_pk_required_error(self):
        mdl = await RequiredPKModel.create(id="A", name="name_a")
        with self.assertRaises(ParamsError):
            mdl.clone()

    async def test_clone_pk_required(self):
        mdl = await RequiredPKModel.create(id="A", name="name_a")
        mdl2 = mdl.clone(pk="B")
        await mdl2.save()
        mdls = list(await RequiredPKModel.all())
        self.assertEqual(len(mdls), 2)

    async def test_implicit_clone_pk_required_none(self):
        mdl = await RequiredPKModel.create(id="A", name="name_a")
        mdl.pk = None
        with self.assertRaises(ValidationError):
            await mdl.save()


class TestModelMethods(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.cls = Tournament
        self.mdl = await self.cls.create(name="Test")
        self.mdl2 = self.cls(name="Test")

    async def test_save(self):
        oldid = self.mdl.id
        await self.mdl.save()
        self.assertEqual(self.mdl.id, oldid)

    async def test_save_f_expression(self):
        int_field = await IntFields.create(intnum=1)
        int_field.intnum = F("intnum") + 1
        await int_field.save(update_fields=["intnum"])
        n_int = await IntFields.get(pk=int_field.pk)
        self.assertEqual(n_int.intnum, 2)

    async def test_save_full(self):
        self.mdl.name = "TestS"
        self.mdl.desc = "Something"
        await self.mdl.save()
        n_mdl = await self.cls.get(id=self.mdl.id)
        self.assertEqual(n_mdl.name, "TestS")
        self.assertEqual(n_mdl.desc, "Something")

    async def test_save_partial(self):
        self.mdl.name = "TestS"
        self.mdl.desc = "Something"
        await self.mdl.save(update_fields=["desc"])
        n_mdl = await self.cls.get(id=self.mdl.id)
        self.assertEqual(n_mdl.name, "Test")
        self.assertEqual(n_mdl.desc, "Something")

    async def test_save_partial_with_pk_update(self):
        # Not allow to update pk field only
        with self.assertRaisesRegex(OperationalError, "Can't update pk field"):
            await self.mdl.save(update_fields=["id"])
        # So does update pk field with others
        with self.assertRaisesRegex(OperationalError, f"use `{self.cls.__name__}.create` instead"):
            await self.mdl.save(update_fields=["id", "desc"])

    async def test_create(self):
        mdl = self.cls(name="Test2")
        self.assertIsNone(mdl.id)
        await mdl.save()
        self.assertIsNotNone(mdl.id)

    async def test_delete(self):
        mdl = await self.cls.get(name="Test")
        self.assertEqual(self.mdl.id, mdl.id)

        await self.mdl.delete()

        with self.assertRaises(DoesNotExist):
            await self.cls.get(name="Test")

        with self.assertRaises(OperationalError):
            await self.mdl2.delete()

    def test_str(self):
        self.assertEqual(str(self.mdl), "Test")

    def test_repr(self):
        self.assertEqual(repr(self.mdl), f"<Tournament: {self.mdl.id}>")
        self.assertEqual(repr(self.mdl2), "<Tournament>")

    def test_hash(self):
        self.assertEqual(hash(self.mdl), self.mdl.id)
        with self.assertRaises(TypeError):
            hash(self.mdl2)

    async def test_eq(self):
        mdl = await self.cls.get(name="Test")
        self.assertEqual(self.mdl, mdl)

    async def test_get_or_create(self):
        mdl, created = await self.cls.get_or_create(name="Test")
        self.assertFalse(created)
        self.assertEqual(self.mdl, mdl)
        mdl, created = await self.cls.get_or_create(name="Test2")
        self.assertTrue(created)
        self.assertNotEqual(self.mdl, mdl)
        mdl2 = await self.cls.get(name="Test2")
        self.assertEqual(mdl, mdl2)

    async def test_update_or_create(self):
        mdl, created = await self.cls.update_or_create(name="Test")
        self.assertFalse(created)
        self.assertEqual(self.mdl, mdl)
        mdl, created = await self.cls.update_or_create(name="Test2")
        self.assertTrue(created)
        self.assertNotEqual(self.mdl, mdl)
        mdl2 = await self.cls.get(name="Test2")
        self.assertEqual(mdl, mdl2)

    async def test_update_or_create_with_defaults(self):
        mdl = await self.cls.get(name=self.mdl.name)
        mdl_dict = dict(mdl)
        oldid = mdl.id
        mdl.id = 135
        with self.assertRaisesRegex(ParamsError, "Conflict value with key='id':"):
            # Missing query: check conflict with kwargs and defaults before create
            await self.cls.update_or_create(id=mdl.id, defaults=mdl_dict)
        desc = str(uuid4())
        # If there is no conflict with defaults and kwargs, it will be success to update or create
        defaults = dict(mdl_dict, desc=desc)
        kwargs = {"id": defaults["id"], "name": defaults["name"]}
        mdl, created = await self.cls.update_or_create(defaults, **kwargs)
        self.assertFalse(created)
        self.assertEqual(defaults["desc"], mdl.desc)
        self.assertNotEqual(self.mdl.desc, mdl.desc)
        # Hint query: use defauts to update without checking conflict
        mdl2, created = await self.cls.update_or_create(
            id=oldid, desc=desc, defaults=dict(mdl_dict, desc="new desc")
        )
        self.assertFalse(created)
        self.assertNotEqual(dict(mdl), dict(mdl2))
        # Missing query: success to create if no conflict
        not_exist_name = str(uuid4())
        no_conflict_defaults = {"name": not_exist_name, "desc": desc}
        no_conflict_kwargs = {"name": not_exist_name}
        mdl, created = await self.cls.update_or_create(no_conflict_defaults, **no_conflict_kwargs)
        self.assertTrue(created)
        self.assertEqual(not_exist_name, mdl.name)

    async def test_first(self):
        mdl = await self.cls.first()
        self.assertEqual(self.mdl.id, mdl.id)

    async def test_last(self):
        mdl = await self.cls.last()
        self.assertEqual(self.mdl.id, mdl.id)

    async def test_latest(self):
        mdl = await self.cls.latest("name")
        self.assertEqual(self.mdl.id, mdl.id)

    async def test_earliest(self):
        mdl = await self.cls.earliest("name")
        self.assertEqual(self.mdl.id, mdl.id)

    async def test_filter(self):
        mdl = await self.cls.filter(name="Test").first()
        self.assertEqual(self.mdl.id, mdl.id)
        mdl = await self.cls.filter(name="Test2").first()
        self.assertIsNone(mdl)

    async def test_all(self):
        mdls = list(await self.cls.all())
        self.assertEqual(len(mdls), 1)
        self.assertEqual(mdls, [self.mdl])

    async def test_get(self):
        mdl = await self.cls.get(name="Test")
        self.assertEqual(self.mdl.id, mdl.id)

        with self.assertRaises(DoesNotExist):
            await self.cls.get(name="Test2")

        await self.cls.create(name="Test")

        with self.assertRaises(MultipleObjectsReturned):
            await self.cls.get(name="Test")

    async def test_exists(self):
        await self.cls.create(name="Test")
        ret = await self.cls.exists(name="Test")
        self.assertTrue(ret)

        ret = await self.cls.exists(name="XXX")
        self.assertFalse(ret)

        ret = await self.cls.exists(Q(name="XXX") & Q(name="Test"))
        self.assertFalse(ret)

    async def test_get_or_none(self):
        mdl = await self.cls.get_or_none(name="Test")
        self.assertEqual(self.mdl.id, mdl.id)

        mdl = await self.cls.get_or_none(name="Test2")
        self.assertEqual(mdl, None)

        await self.cls.create(name="Test")

        with self.assertRaises(MultipleObjectsReturned):
            await self.cls.get_or_none(name="Test")

    @test.skipIf(os.name == "nt", "timestamp issue on Windows")
    async def test_update_from_dict(self):
        evt1 = await Event.create(name="a", tournament=await Tournament.create(name="a"))
        orig_modified = evt1.modified
        await evt1.update_from_dict({"alias": "8", "name": "b", "bad_name": "foo"}).save()
        self.assertEqual(evt1.alias, 8)
        self.assertEqual(evt1.name, "b")

        with self.assertRaises(AttributeError):
            _ = evt1.bad_name

        evt2 = await Event.get(name="b")
        self.assertEqual(evt1.pk, evt2.pk)
        self.assertEqual(evt1.modified, evt2.modified)
        self.assertNotEqual(orig_modified, evt1.modified)

        with self.assertRaises(ConfigurationError):
            await evt2.update_from_dict({"participants": []})

        with self.assertRaises(ValueError):
            await evt2.update_from_dict({"alias": "foo"})

    async def test_index_access(self):
        obj = await self.cls[self.mdl.pk]
        self.assertEqual(obj, self.mdl)

    async def test_index_badval(self):
        with self.assertRaises(ObjectDoesNotExistError) as cm:
            await self.cls[32767]
        the_exception = cm.exception
        # For compatibility reasons this should be an instance of KeyError
        self.assertIsInstance(the_exception, KeyError)
        self.assertIs(the_exception.model, self.cls)
        self.assertEqual(the_exception.pk_name, "id")
        self.assertEqual(the_exception.pk_val, 32767)
        self.assertEqual(str(the_exception), f"{self.cls.__name__} has no object with id=32767")

    async def test_index_badtype(self):
        with self.assertRaises(ObjectDoesNotExistError) as cm:
            await self.cls["asdf"]
        the_exception = cm.exception
        # For compatibility reasons this should be an instance of KeyError
        self.assertIsInstance(the_exception, KeyError)
        self.assertIs(the_exception.model, self.cls)
        self.assertEqual(the_exception.pk_name, "id")
        self.assertEqual(the_exception.pk_val, "asdf")
        self.assertEqual(str(the_exception), f"{self.cls.__name__} has no object with id=asdf")

    async def test_clone(self):
        mdl2 = self.mdl.clone()
        self.assertEqual(mdl2.pk, None)
        await mdl2.save()
        self.assertNotEqual(mdl2.pk, self.mdl.pk)
        mdls = list(await self.cls.all())
        self.assertEqual(len(mdls), 2)

    async def test_clone_with_pk(self):
        mdl2 = self.mdl.clone(pk=8888)
        self.assertEqual(mdl2.pk, 8888)
        await mdl2.save()
        self.assertNotEqual(mdl2.pk, self.mdl.pk)
        await mdl2.save()
        mdls = list(await self.cls.all())
        self.assertEqual(len(mdls), 2)

    async def test_clone_from_db(self):
        mdl2 = await self.cls.get(pk=self.mdl.pk)
        mdl3 = mdl2.clone()
        mdl3.pk = None
        await mdl3.save()
        self.assertNotEqual(mdl3.pk, mdl2.pk)
        mdls = list(await self.cls.all())
        self.assertEqual(len(mdls), 2)

    async def test_implicit_clone(self):
        self.mdl.pk = None
        await self.mdl.save()
        mdls = list(await self.cls.all())
        self.assertEqual(len(mdls), 2)

    async def test_force_create(self):
        obj = self.cls(name="Test", id=self.mdl.id)
        with self.assertRaises(IntegrityError):
            await obj.save(force_create=True)

    async def test_force_update(self):
        obj = self.cls(name="Test3", id=self.mdl.id)
        await obj.save(force_update=True)

    async def test_force_update_raise(self):
        obj = self.cls(name="Test3", id=self.mdl.id + 100)
        with self.assertRaises(IntegrityError):
            await obj.save(force_update=True)

    async def test_raw(self):
        await Node.create(name="TestRaw")
        ret = await Node.raw("select * from node where name='TestRaw'")
        self.assertEqual(len(ret), 1)
        ret = await Node.raw("select * from node where name='111'")
        self.assertEqual(len(ret), 0)


class TestModelMethodsNoID(TestModelMethods):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.mdl = await NoID.create(name="Test")
        self.mdl2 = NoID(name="Test")
        self.cls = NoID

    def test_str(self):
        self.assertEqual(str(self.mdl), "<NoID>")

    def test_repr(self):
        self.assertEqual(repr(self.mdl), f"<NoID: {self.mdl.id}>")
        self.assertEqual(repr(self.mdl2), "<NoID>")


class TestModelConstructor(test.TestCase):
    def test_null_in_nonnull_field(self):
        with self.assertRaisesRegex(ValueError, "name is non nullable field, but null was passed"):
            Event(name=None)

    def test_rev_fk(self):
        with self.assertRaisesRegex(
            ConfigurationError,
            "You can't set backward relations through init, change related model instead",
        ):
            Tournament(name="a", events=[])

    def test_m2m(self):
        with self.assertRaisesRegex(
            ConfigurationError, "You can't set m2m relations through init, use m2m_manager instead"
        ):
            Event(name="a", participants=[])

    def test_rev_m2m(self):
        with self.assertRaisesRegex(
            ConfigurationError, "You can't set m2m relations through init, use m2m_manager instead"
        ):
            Team(name="a", events=[])

    async def test_rev_o2o(self):
        with self.assertRaisesRegex(
            ConfigurationError,
            "You can't set backward one to one relations through init, "
            "change related model instead",
        ):
            address = await O2O_null.create(name="Ocean")
            await Dest_null(name="a", address_null=address)

    def test_fk_unsaved(self):
        with self.assertRaisesRegex(OperationalError, "You should first call .save()"):
            Event(name="a", tournament=Tournament(name="a"))

    async def test_fk_saved(self):
        await Event.create(name="a", tournament=await Tournament.create(name="a"))

    async def test_noneawaitable(self):
        self.assertFalse(NoneAwaitable)
        self.assertIsNone(await NoneAwaitable)
        self.assertFalse(NoneAwaitable)
        self.assertIsNone(await NoneAwaitable)
