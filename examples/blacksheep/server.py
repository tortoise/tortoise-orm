# pylint: disable=E0401,E0611
from __future__ import annotations

from uuid import UUID

from blacksheep import Response
from blacksheep.server import Application
from blacksheep.server.openapi.v3 import Info, OpenAPIHandler
from blacksheep.server.responses import created, no_content, ok
from models import UserPydanticIn, UserPydanticOut, Users

from tortoise.contrib.blacksheep import register_tortoise

app = Application()
register_tortoise(
    app,
    db_url="sqlite://:memory:",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


docs = OpenAPIHandler(info=Info(title="Tortoise ORM BlackSheep example", version="0.0.1"))
docs.bind_app(app)


@app.router.get("/")
async def users_list() -> UserPydanticOut:
    return ok(await UserPydanticOut.from_queryset(Users.all()))


@app.router.post("/")
async def users_create(user: UserPydanticIn) -> UserPydanticOut:
    user = await Users.create(**user.model_dump(exclude_unset=True))
    return created(await UserPydanticOut.from_tortoise_orm(user))


@app.router.patch("/{id}")
async def users_patch(id: UUID, user: UserPydanticIn) -> UserPydanticOut:
    await Users.filter(id=id).update(**user.model_dump(exclude_unset=True))
    return ok(await UserPydanticOut.from_tortoise_orm(await Users.get(id=id)))


@app.router.put("/{id}")
async def users_put(id: UUID, user: UserPydanticIn) -> UserPydanticOut:
    await Users.filter(id=id).update(**user.model_dump())
    return ok(await UserPydanticOut.from_tortoise_orm(await Users.get(id=id)))


@app.router.delete("/{id}")
async def users_delete(id: UUID) -> Response:
    await Users.filter(id=id).delete()
    return no_content()
