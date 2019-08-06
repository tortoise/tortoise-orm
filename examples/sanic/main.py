from sanic import Sanic
from sanic import response
from tortoise import Tortoise, Model, fields
from modles import Users

app = Sanic(__name__)

# ----------------------------------------------- #
# Routes
# ----------------------------------------------- #

@app.route("/")
async def list_all(request):
    users = await Users.all()
    return response.json({
        "users": [str(user) for user in users]
    })

@app.route("/user")
async def add_user(request):
    user = await Users.create(name="New User")
    return response.json({
        "user": str(user)
    })

# ----------------------------------------------- #
# Server Start/Stop Hooks
# ----------------------------------------------- #

@app.listener("before_server_start")
async def setup_database(app, loop):
    app.db = await Tortoise.init(
        db_url="sqlite://db.sqlite3",
        modules={"models": ["models"]}
    )
    print("Tortoise-ORM startup")

    await Tortoise.generate_schemas()
    print("Tortoise-ORM generate schemas")

@app.listener("after_server_stop")
async def teardown_database(app, loop):
    await Tortoise.close_connections()
    print("Tortoise-ORM shutdown")

# ----------------------------------------------- #
# Run Server
# ----------------------------------------------- #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
