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
