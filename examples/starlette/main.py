# pylint: disable=E0401,E0611
import logging
from json import JSONDecodeError

from models import Users
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from tortoise.contrib.starlette import register_tortoise

logging.basicConfig(level=logging.DEBUG)


async def list_all(_: Request) -> JSONResponse:
    users = await Users.all()
    return JSONResponse({"users": [str(user) for user in users]})


async def add_user(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        username = payload["username"]
    except JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="cannot parse request body"
        ) from e
    except KeyError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="username is required") from e

    user = await Users.create(username=username)
    return JSONResponse({"user": str(user)}, status_code=HTTP_201_CREATED)


app = Starlette(
    debug=True,
    routes=[
        Route("/", list_all),
        Route("/user", add_user, methods=["POST"]),
    ],
)
register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["models"]}, generate_schemas=True
)

if __name__ == "__main__":
    from uvicorn.main import run

    run(app)
