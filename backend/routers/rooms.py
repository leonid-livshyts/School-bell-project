from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from fastapi import HTTPException, status, APIRouter, Depends
from pydantic import BaseModel
from models import Lesson, Room
from routers.db_tools import db_dependency
from routers.oauth_tools import oauth2


class RoomObj(BaseModel):
    name: str


rooms_router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
    dependencies=[Depends(oauth2)]
)


@rooms_router.get("/", status_code=status.HTTP_200_OK)
async def read_all_rooms(db: db_dependency):
    query = select(Room)
    result = await db.execute(query)
    return result.scalars().all()


@rooms_router.get("/{room_id}", status_code=status.HTTP_200_OK)
async def read_room_by_id(db: db_dependency, room_id: int):
    query = select(Room).where(Room.id == room_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    if room is not None:
        return room
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")


@rooms_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_room(db: db_dependency, room_obj: RoomObj):
    new_room = Room(**room_obj.model_dump())
    db.add(new_room)
    try:
        await db.commit()
    except IntegrityError as ie:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room already exists") from ie


@rooms_router.post("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_room_by_id(db: db_dependency, room_obj: RoomObj, room_id: int):
    query = select(Room).where(Room.id == room_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    room.name = room_obj.name

    try:
        await db.commit()
    except IntegrityError as ie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A room with this name already exists",
        ) from ie


@rooms_router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_by_id(db: db_dependency, room_id: int):
    query = select(Room).where(Room.id == room_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    try:
        await db.delete(room)
        await db.commit()
    except IntegrityError as ie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is still referenced by lessons/devices/measures/etc.",
        ) from ie
