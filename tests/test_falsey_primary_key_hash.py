import pytest

from tests.testmodels import IntFields, RequiredPKModel


@pytest.mark.parametrize(
    "model", [IntFields(id=0, intnum=1), RequiredPKModel(id="", name="example")]
)
def test_model_with_falsey_primary_key_is_hashable(model):
    assert hash(model) == hash(model.pk)
