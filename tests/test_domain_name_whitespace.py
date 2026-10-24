import pytest

from tortoise.validators import DomainNameValidator, InvalidDomainName


@pytest.mark.parametrize("accept_idna", [False, True])
def test_domain_name_rejects_trailing_newline(accept_idna):
    validator = DomainNameValidator(accept_idna=accept_idna)
    with pytest.raises(InvalidDomainName):
        validator("example.com\n")
    validator("example.com")
    validator("example.com.")
