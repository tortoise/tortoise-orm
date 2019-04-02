import asyncio
import json
from random import choice

from quart import Quart

from tortoise import Tortoise, fields
from tortoise.models import Model

STATUSES = ["New", "Old", "Gone"]
app = Quart(__name__)


class Users(Model):
    id = fields.IntField(pk=True)
    status = fields.CharField(20)

    def __str__(self):
        return "User {}: {}".format(self.id, self.status)


class Workers(Model):
    id = fields.IntField(pk=True)
    status = fields.CharField(20)

    def __str__(self):
        return "Worker {}: {}".format(self.id, self.status)


@app.before_serving
async def init_orm():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()


@app.after_serving
async def close_orm():
    await Tortoise.close_connections()


@app.route("/")
async def list_all():
    users, workers = await asyncio.gather(Users.all(), Workers.all())
    return json.dumps(
        {
            "users": [str(user) for user in users],
            "workers": [str(worker) for worker in workers],
        },
        indent=4,
    )


@app.route("/user")
async def add_user():
    user = await Users.create(status=choice(STATUSES))
    return str(user)


@app.route("/worker")
async def add_worker():
    worker = await Workers.create(status=choice(STATUSES))
    return str(worker)


if __name__ == "__main__":
    app.run(port=5000)
