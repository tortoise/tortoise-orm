from sanic import Sanic, response

from models import Users
from tortoise.contrib.sanic import register_tortoise

app = Sanic(__name__)


@app.route("/")
async def list_all(request):
    users = await Users.all()
    return response.json({"users": [str(user) for user in users]})


@app.route("/user")
async def add_user(request):
    user = await Users.create(name="New User")
    return response.json({"user": str(user)})


register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["models"]}, generate_schemas=True
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
