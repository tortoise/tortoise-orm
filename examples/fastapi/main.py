from typing import List

from fastapi import FastAPI

from tortoise import fields, models
from tortoise.contrib.fastapi import HTTPNotFoundError, register_tortoise
from tortoise.contrib.pydantic import pydantic_model_creator


class Users(models.Model):
    """
    This contains users

    Starting off very basic.
    """

    id = fields.IntField(pk=True)
    #: This is a username
    username = fields.CharField(max_length=20)

    def pretty_name(self) -> str:
        """
        Returns a prettified name
        """
        return f"User {self.id}: {self.username}"

    class PydanticMeta:
        computed = ["pretty_name"]


User_Pydantic = pydantic_model_creator(Users, name="User")
app = FastAPI()


@app.get("/users", response_model=List[User_Pydantic])
async def get_users():
    return await User_Pydantic.from_queryset(Users.all())


@app.post("/users", response_model=User_Pydantic)
async def create_user(user: User_Pydantic):
    data = user.dict()
    data.pop("id", None)
    user_obj = await Users.create(**data)
    return await User_Pydantic.from_tortoise_orm(user_obj)


@app.get(
    "/user/{user_id}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def get_user(user_id: int):
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["__main__"]}, generate_schemas=True
)
