# pylint: disable=E0401,E0611
import logging

from models import User
from sanic import Sanic, response

from tortoise.contrib.sanic import register_tortoise

logging.basicConfig(level=logging.DEBUG)

app = Sanic(__name__)


@app.route("/")
async def list_all(request):
    users = await User.all()
    return response.json({"users": [user.to_json() for user in users]})


@app.route("/user", methods=["POST"])
async def add_user(request):
    user = await User.create(name="New User")
    return response.json(user.to_json())


register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["models"]}, generate_schemas=True
)


if __name__ == "__main__":
    app.run(port=5000)
