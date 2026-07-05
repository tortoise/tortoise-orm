import pytest

from tests.testmodels import MyAbstractBaseModel, MyDerivedModel


@pytest.mark.asyncio
async def test_basic(db):
    """Test basic model inheritance with abstract base model."""
    model = MyDerivedModel(name="test")
    assert hasattr(MyAbstractBaseModel(), "name")
    assert hasattr(model, "created_at")
    assert hasattr(model, "modified_at")
    assert hasattr(model, "name")
    assert hasattr(model, "first_name")
    await model.save()
    assert model.created_at is not None
    assert model.modified_at is not None


def test_abstract_meta_ordering_is_inherited():
    """A subclass without its own ``Meta.ordering`` inherits the abstract
    base's ordering, while a subclass that defines its own keeps it and an
    explicitly empty ordering stays empty (#2046)."""
    from tortoise import fields
    from tortoise.models import Model

    class OrderedBase(Model):
        value = fields.IntField()

        class Meta:
            abstract = True
            ordering = ["-value"]

    class InheritsOrdering(OrderedBase):
        class Meta:
            abstract = True

    class OwnOrdering(OrderedBase):
        class Meta:
            abstract = True
            ordering = ["value"]

    class EmptyOrdering(OrderedBase):
        class Meta:
            abstract = True
            ordering = []

    assert OrderedBase._meta._default_ordering != ()
    assert InheritsOrdering._meta._default_ordering == OrderedBase._meta._default_ordering
    assert OwnOrdering._meta._default_ordering != OrderedBase._meta._default_ordering
    assert EmptyOrdering._meta._default_ordering == ()
