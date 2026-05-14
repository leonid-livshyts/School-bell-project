from typing import Annotated, Optional
from secrets import token_hex
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from routers.db_tools import db_dependency
from models import User, Session
from routers.password_tools import hash_password


class UserObj(BaseModel):
    username: str
    password1: str
    password2: str
    email: Optional[str]
    role: Optional[str]

auth_router = APIRouter()




@auth_router.post("/login", response_model=dict)
async def login(
    db: db_dependency,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = await User.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong credentials")

    session_token = token_hex(32)
    new_session = Session(
        token=session_token,
        expired_at=datetime.now(ZoneInfo("Europe/Kyiv")) + timedelta(hours=2),
        user_id=user.id
    )
    db.add(new_session)
    await db.commit()

    return {"access_token": session_token, "token_type": "bearer"}


@auth_router.post("/register")
async def register(db: db_dependency, user_obj: UserObj):
    if user_obj.password1 != user_obj.password2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password don't match")

    if not user_obj.password1.isascii():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong password format")

    e_user = await User.find_by_username(db, user_obj.username)
    if e_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is taken")

    hashed_password = hash_password(user_obj.password1)
    new_user = User(
        username=user_obj.username,
        hashed_password=hashed_password,
        email=user_obj.email,
        role=user_obj.role or "user"
    )
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError as ie:
        if "email" in str(ie):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists") from ie
        elif "username" in str(ie):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="User with this username already exists") from ie
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unexpected") from ie