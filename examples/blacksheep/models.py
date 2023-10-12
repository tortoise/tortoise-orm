import tortoise
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

if tortoise.__version__ >= "0.20":
    raise RuntimeError("blacksheep not support pydantic V2, use tortoise-orm<0.20 instead!")


class Users(models.Model):
    id = fields.UUIDField(pk=True)
    username = fields.CharField(max_length=63)

    def __str__(self) -> str:
        return f"User {self.id}: {self.username}"


UserPydanticOut = pydantic_model_creator(Users, name="UserOut")
UserPydanticIn = pydantic_model_creator(Users, name="UserIn", exclude_readonly=True)
