from decimal import Decimal

import pytest

from tortoise.exceptions import ValidationError
from tortoise.validators import MaxValueValidator, MinValueValidator


@pytest.mark.parametrize("validator_class", [MinValueValidator, MaxValueValidator])
@pytest.mark.parametrize("value", [float("nan"), Decimal("NaN"), Decimal("sNaN")])
def test_range_validator_rejects_nan_values(validator_class, value):
    with pytest.raises(ValidationError):
        validator_class(0)(value)


@pytest.mark.parametrize("validator_class", [MinValueValidator, MaxValueValidator])
@pytest.mark.parametrize("value", [float("nan"), Decimal("NaN"), Decimal("sNaN")])
def test_range_validator_rejects_nan_bounds(validator_class, value):
    with pytest.raises(ValidationError):
        validator_class(value)
