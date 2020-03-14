# pylint: disable=E0611
from typing import List

from fastapi import FastAPI

from models import User_Pydantic, UserIn_Pydantic, Users
from tortoise.contrib.fastapi import HTTPNotFoundError, register_tortoise

app = FastAPI(title="Tortoise ORM FastAPI example")


@app.get("/users", response_model=List[User_Pydantic])
async def get_users():
    return await User_Pydantic.from_queryset(Users.all())


@app.post("/users", response_model=User_Pydantic)
async def create_user(user: UserIn_Pydantic):
    user_obj = await Users.create(**user.dict())
    return await User_Pydantic.from_tortoise_orm(user_obj)


@app.get(
    "/user/{user_id}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def get_user(user_id: int):
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@app.post(
    "/user/{user_id}", response_model=User_Pydantic, responses={404: {"model": HTTPNotFoundError}}
)
async def update_user(user_id: int, user: UserIn_Pydantic):
    await Users.filter(id=user_id).update(**user.dict())
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["models"]}, generate_schemas=True
)
