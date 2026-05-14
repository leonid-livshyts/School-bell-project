from fastapi import Security, Depends, HTTPException, status
from routers.db_tools import db_dependency
from models import Device, User, Session
from sqlalchemy.future import select
from fastapi.security.api_key import APIKeyHeader
from typing import Annotated
from routers.cookie_tools import cookie_dependency


api_key_header = APIKeyHeader(name="X-API-Key")

async def get_room_id(db: db_dependency, api_key: str = Security(api_key_header)):
    query = select(Device).where((Device.key == api_key))
    result = await db.execute(query)
    device = result.scalar_one_or_none()

    return device.room_id

room_id_db_dependency = Annotated[int, Depends(get_room_id)]


async def get_user_id(db: db_dependency, cookies: cookie_dependency):
    query = select(Session).where(Session.token == cookies.session)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=status.HTTP_418_IM_A_TEAPOT)

    return session.user_id


session_db_dependency = Annotated[int, Depends(get_user_id)]