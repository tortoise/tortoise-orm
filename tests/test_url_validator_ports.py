import pytest

from tortoise.validators import InvalidScheme, InvalidURL, URLValidator


def test_url_validator_rejects_out_of_range_port():
    validator = URLValidator()
    with pytest.raises(InvalidURL):
        validator("http://example.com:65536")
    validator("http://example.com:65535")


@pytest.mark.parametrize("port", ["65536", "abc"])
def test_url_validator_preserves_scheme_error(port):
    validator = URLValidator(allowed_schemes=["http"])
    with pytest.raises(InvalidScheme):
        validator(f"ftp://example.com:{port}")
