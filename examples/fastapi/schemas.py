from __future__ import annotations

from typing import TYPE_CHECKING

from models import Users
from pydantic import BaseModel

from tortoise.contrib.pydantic import PydanticModel, pydantic_model_creator

if TYPE_CHECKING:  # pragma: nocoverage

    class UserIn_Pydantic(Users, PydanticModel):  # type:ignore[misc]
        pass

    class User_Pydantic(Users, PydanticModel):  # type:ignore[misc]
        pass

else:
    User_Pydantic = pydantic_model_creator(Users, name="User")
    UserIn_Pydantic = pydantic_model_creator(Users, name="UserIn", exclude_readonly=True)


class Status(BaseModel):
    message: str
