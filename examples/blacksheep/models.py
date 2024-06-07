from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class Users(models.Model):
    id = fields.UUIDField(primary_key=True)
    username = fields.CharField(max_length=63)

    def __str__(self) -> str:
        return f"User {self.id}: {self.username}"


UserPydanticOut = pydantic_model_creator(Users, name="UserOut")
UserPydanticIn = pydantic_model_creator(Users, name="UserIn", exclude_readonly=True)
