# pylint: disable=E0401,E0611
import logging
from json import JSONDecodeError

from models import Users
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from uvicorn.main import run

from tortoise.contrib.starlette import register_tortoise

logging.basicConfig(level=logging.DEBUG)

app = Starlette()


@app.route("/", methods=["GET"])
async def list_all(_: Request) -> JSONResponse:
    users = await Users.all()
    return JSONResponse({"users": [str(user) for user in users]})


@app.route("/user", methods=["POST"])
async def add_user(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        username = payload["username"]
    except JSONDecodeError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="cannot parse request body")
    except KeyError:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="username is required")

    user = await Users.create(username=username)
    return JSONResponse({"user": str(user)}, status_code=HTTP_201_CREATED)


register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["models"]}, generate_schemas=True
)

if __name__ == "__main__":
    run(app)
