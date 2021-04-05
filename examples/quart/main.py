# pylint: disable=E0401,E0611
import asyncio
import logging
from random import choice

from models import Users, Workers
from quart import Quart, jsonify

from tortoise.contrib.quart import register_tortoise

logging.basicConfig(level=logging.DEBUG)


STATUSES = ["New", "Old", "Gone"]
app = Quart(__name__)


@app.route("/")
async def list_all():
    users, workers = await asyncio.gather(Users.all(), Workers.all())
    return jsonify(
        {"users": [str(user) for user in users], "workers": [str(worker) for worker in workers]}
    )


@app.route("/user")
async def add_user():
    user = await Users.create(status=choice(STATUSES))  # nosec
    return str(user)


@app.route("/worker")
async def add_worker():
    worker = await Workers.create(status=choice(STATUSES))  # nosec
    return str(worker)


register_tortoise(
    app,
    db_url="mysql://root:@127.0.0.1:3306/quart",
    modules={"models": ["models"]},
    generate_schemas=False,
)


if __name__ == "__main__":
    app.run(port=5000)
