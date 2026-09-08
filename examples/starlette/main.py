#!/usr/bin/env python
# pylint: disable=E0401,E0611
import logging
from json import JSONDecodeError
from pathlib import Path

from models import Users
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from tortoise.contrib.starlette import register_tortoise

logging.basicConfig(level=logging.DEBUG)

app = Starlette()


async def list_all(_: Request) -> JSONResponse:
    users = await Users.all()
    return JSONResponse({"users": [str(user) for user in users]})


async def add_user(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        username = payload["username"]
    except JSONDecodeError:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="cannot parse request body"
        ) from None
    except KeyError:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="username is required"
        ) from None

    user = await Users.create(username=username)
    return JSONResponse({"user": repr(user)}, status_code=HTTP_201_CREATED)


app = Starlette(
    routes=[
        Route("/", list_all),
        Mount("/user", routes=[Route("/", add_user, methods=["POST"])]),
    ]
)
register_tortoise(
    app, db_url="sqlite://:memory:", modules={"models": ["models"]}, generate_schemas=True
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("__main__:app", reload=True, reload_dirs=[str(Path(__file__).parent)])
