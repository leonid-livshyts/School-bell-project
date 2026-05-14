from typing import Annotated
from fastapi import Security, HTTPException, Depends, status
from sqlalchemy.future import select
from fastapi.security.api_key import APIKeyHeader
from routers.db_tools import db_dependency
from models import Device


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def get_room_id(db: db_dependency, api_key: str = Security(api_key_header)):
    query = select(Device).where(Device.key == api_key)
    result = await db.execute(query)
    ring = result.scalar_one_or_none()

    if not ring:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")

    return ring.room_id


room_id_dependency = Annotated[int, Depends(get_room_id)]
