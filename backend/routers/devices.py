from fastapi import HTTPException, status, APIRouter, Depends
from models import Device
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from routers.db_tools import db_dependency
from routers.oauth_tools import oauth2
from datetime import datetime

class DeviceObj(BaseModel):
    key: str
    version: str
    installed_date: datetime


devices_router = APIRouter(
    prefix="/{room_id}/devices",
    tags=["rooms", "devices"],
    dependencies=[Depends(oauth2)],
)

@devices_router.get("/", status_code=status.HTTP_200_OK)
async def read_all_devices_by_room(db: db_dependency, room_id: int):
    query = select(Device).where(Device.room_id == room_id)
    result = await db.execute(query)
    return result.scalars().all()

@devices_router.get("/{device_id}", status_code=status.HTTP_200_OK)
async def read_devices_by_id(db: db_dependency, room_id: int, device_id: int):
    query = select(Device).where((Device.id == device_id) & (Device.room_id == room_id))
    result = await db.execute(query)
    device = result.scalar_one_or_none()

    if device is not None:
        return device

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")

@devices_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_device(db: db_dependency, device_obj: DeviceObj, room_id: int):
    new_device = Device(**device_obj.model_dump(), room_id=room_id)
    db.add(new_device)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No such room")

@devices_router.post("/{device_id}", status_code=status.HTTP_200_OK)
async def update_device_by_id(db: db_dependency, device_obj: DeviceObj, room_id: int, device_id: int):
    query = select(Device).where((Device.id == device_id) & (Device.room_id == room_id))
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="room not found")

    device.key = device_obj.key
    device.version = device_obj.version
    device.installed_date = device_obj.installed_date

    try:
        await db.commit()
    except IntegrityError as ie:
        if "UNIQUE" in str(ie):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="There is a room with such name")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No such room")

@devices_router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_by_id(db: db_dependency, room_id: int, device_id: int):
    print(room_id, device_id)
    query = select(Device).where((Device.id == device_id) & (Device.room_id == room_id))
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")

    await db.delete(device)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No such room")