from sqlalchemy.future import select
from fastapi import HTTPException, status, APIRouter, Depends
from pydantic import BaseModel
from models import Alarm, Room
from routers.db_tools import db_dependency
from routers.oauth_tools import oauth2


class AlarmObj(BaseModel):
    is_active: bool


alarms_router = APIRouter(
    prefix="/alarms",
    tags=["alarms"],
    dependencies=[Depends(oauth2)],
)


@alarms_router.get("/", status_code=status.HTTP_200_OK)
async def read_all_alarms(db: db_dependency):
    """List the alarm state of every room."""
    result = await db.execute(select(Alarm))
    return result.scalars().all()


@alarms_router.post("/{room_id}", status_code=status.HTTP_200_OK)
async def set_alarm(db: db_dependency, room_id: int, alarm_obj: AlarmObj):
    """Turn the alarm on or off for a room.

    The device polls GET /private/alarm and starts/stops the alarm sound when
    this flag changes.
    """
    room = (await db.execute(
        select(Room).where(Room.id == room_id)
    )).scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Reuse the room's alarm row if it exists, otherwise create one.
    alarm = (await db.execute(
        select(Alarm).where(Alarm.room_id == room_id)
    )).scalar_one_or_none()
    if alarm is None:
        alarm = Alarm(room_id=room_id, is_active=alarm_obj.is_active)
        db.add(alarm)
    else:
        alarm.is_active = alarm_obj.is_active

    await db.commit()
    print(f"[ALARM] room_id={room_id} set to is_active={alarm_obj.is_active}")
    return {"room_id": room_id, "is_active": alarm_obj.is_active}
