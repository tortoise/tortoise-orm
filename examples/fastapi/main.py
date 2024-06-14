# pylint: disable=E0611,E0401
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator, List

from fastapi import FastAPI, HTTPException
from models import Users
from pydantic import BaseModel

from tortoise.contrib.fastapi import RegisterTortoise
from tortoise.contrib.pydantic import PydanticModel

if TYPE_CHECKING:  # pragma: nocoverage

    class UserIn_Pydantic(Users, PydanticModel):  # type:ignore[misc]
        pass

    class User_Pydantic(Users, PydanticModel):  # type:ignore[misc]
        pass

else:
    from models import User_Pydantic, UserIn_Pydantic


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    async with RegisterTortoise(
        app,
        db_url="sqlite://:memory:",
        modules={"models": ["models"]},
        generate_schemas=True,
        add_exception_handlers=True,
    ):
        # db connected
        yield
        # app teardown
    # db connections closed


@asynccontextmanager
async def lifespan_east(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    async with RegisterTortoise(
        app,
        db_url="sqlite://:memory:",
        modules={"models": ["models"]},
        generate_schemas=True,
        add_exception_handlers=True,
        use_tz=False,
        timezone="Asia/Shanghai",
    ):
        # db connected
        yield
        # app teardown
    # db connections closed


app = FastAPI(title="Tortoise ORM FastAPI example", lifespan=lifespan)
app_east = FastAPI(title="Tortoise ORM FastAPI example", lifespan=lifespan_east)


class Status(BaseModel):
    message: str


@app.get("/users", response_model=List[User_Pydantic])
async def get_users():
    return await User_Pydantic.from_queryset(Users.all())


@app.post("/users", response_model=User_Pydantic)
async def create_user(user: UserIn_Pydantic):
    user_obj = await Users.create(**user.model_dump(exclude_unset=True))
    return await User_Pydantic.from_tortoise_orm(user_obj)


@app.get("/user/{user_id}", response_model=User_Pydantic)
async def get_user(user_id: int):
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@app.put("/user/{user_id}", response_model=User_Pydantic)
async def update_user(user_id: int, user: UserIn_Pydantic):
    await Users.filter(id=user_id).update(**user.model_dump(exclude_unset=True))
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@app.delete("/user/{user_id}", response_model=Status)
async def delete_user(user_id: int):
    deleted_count = await Users.filter(id=user_id).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return Status(message=f"Deleted user {user_id}")


############################ East 8 ############################
@app_east.get("/users_east", response_model=List[User_Pydantic])
async def get_users_east():
    return await User_Pydantic.from_queryset(Users.all())


@app_east.post("/users_east", response_model=User_Pydantic)
async def create_user_east(user: UserIn_Pydantic):
    user_obj = await Users.create(**user.model_dump(exclude_unset=True))
    return await User_Pydantic.from_tortoise_orm(user_obj)


@app_east.get("/user_east/{user_id}", response_model=User_Pydantic)
async def get_user_east(user_id: int):
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@app_east.put("/user_east/{user_id}", response_model=User_Pydantic)
async def update_user_east(user_id: int, user: UserIn_Pydantic):
    await Users.filter(id=user_id).update(**user.model_dump(exclude_unset=True))
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@app_east.delete("/user_east/{user_id}", response_model=Status)
async def delete_user_east(user_id: int):
    deleted_count = await Users.filter(id=user_id).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return Status(message=f"Deleted user {user_id}")
