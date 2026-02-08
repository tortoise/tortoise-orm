from fastapi import APIRouter, HTTPException
from models import Users
from schemas import Status, User_Pydantic, UserIn_Pydantic

router = APIRouter()


@router.get("/users", response_model=list[User_Pydantic])
async def get_users():
    return await User_Pydantic.from_queryset(Users.all())


@router.post("/users", response_model=User_Pydantic)
async def create_user(user: UserIn_Pydantic):
    user_obj = await Users.create(**user.model_dump(exclude_unset=True))
    return await User_Pydantic.from_tortoise_orm(user_obj)


@router.get("/user/{user_id}", response_model=User_Pydantic)
async def get_user(user_id: int):
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@router.put("/user/{user_id}", response_model=User_Pydantic)
async def update_user(user_id: int, user: UserIn_Pydantic):
    await Users.filter(id=user_id).update(**user.model_dump(exclude_unset=True))
    return await User_Pydantic.from_queryset_single(Users.get(id=user_id))


@router.delete("/user/{user_id}", response_model=Status)
async def delete_user(user_id: int):
    deleted_count = await Users.filter(id=user_id).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return Status(message=f"Deleted user {user_id}")


@router.get("/404")
async def get_404():
    await Users.get(id=0)


@router.get("/422")
async def get_422():
    obj = await Users.create(username="foo")
    await Users.create(username=obj.username)
