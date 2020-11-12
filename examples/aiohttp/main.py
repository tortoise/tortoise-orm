# pylint: disable=E0401,E0611
import logging

from aiohttp import web
from models import Users

from tortoise.contrib.aiohttp import register_tortoise

logging.basicConfig(level=logging.DEBUG)


async def list_all(request):
    users = await Users.all()
    return web.json_response({"users": [str(user) for user in users]})


async def add_user(request):
    user = await Users.create(name="New User")
    return web.json_response({"user": str(user)})


app = web.Application()
app.add_routes([web.get("/", list_all), web.post("/user", add_user)])
register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["models"]}, generate_schemas=True
)


if __name__ == "__main__":
    web.run_app(app, port=5000)
