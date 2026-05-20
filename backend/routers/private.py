from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from fastapi import HTTPException, status, APIRouter, Security
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.future import select
from routers.db_tools import db_dependency
from config import settings_dependency
from routers.security_tools import api_key_header, room_id_dependency
from models import Alarm, Lesson, Measure, Ringtone, VoiceMessage


# The school's local timezone. Lesson times are stored as naive UTC in the DB;
# this is used to work out what "today" means for the device's schedule.
LOCAL_TZ = ZoneInfo("Europe/Kyiv")


class TimeResponse(BaseModel):
    timestamp: int
    timezone_offset: int


class LessonResponse(BaseModel):
    name: str
    start: int
    end: int


class AlarmResponse(BaseModel):
    is_alarm: bool
    ring: bool


class SensorsObj(BaseModel):
    temperature: float
    humidity: float
    volume: float
    air_quality: float
    measure_timestamp: int


class RingtoneResponse(BaseModel):
    code: str


private_router = APIRouter(
    prefix="/private",
    tags=["private"],
)


@private_router.get("/time", status_code=status.HTTP_200_OK)
async def get_current_time():
    offset = datetime.now(ZoneInfo("Europe/Kyiv")).utcoffset()
    return TimeResponse(
        timestamp=int(datetime.now().timestamp()),
        timezone_offset=int(offset.total_seconds()) if offset else 0
    )


@private_router.get("/schedule", response_model=list[LessonResponse],
                    status_code=status.HTTP_200_OK)
async def get_schedule(db: db_dependency, room_id: room_id_dependency):
    # "Today" means today in the school's local timezone. Lesson times are
    # stored as naive UTC, so convert the local day boundaries to naive UTC too.
    now_local = datetime.now(LOCAL_TZ)
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0) \
        .astimezone(timezone.utc).replace(tzinfo=None)
    day_end = now_local.replace(hour=23, minute=59, second=59, microsecond=999999) \
        .astimezone(timezone.utc).replace(tzinfo=None)

    query = select(Lesson).where(
        (Lesson.room_id == room_id) &
        Lesson.start.between(day_start, day_end)
    ).order_by(Lesson.start)
    result = await db.execute(query)
    matched = result.scalars().all()

    # Diagnostic logging: one concise line per poll.
    if not matched:
        other_dates = (await db.execute(
            select(Lesson).where(Lesson.room_id == room_id)
        )).scalars().all()
        print(f"[SCHEDULE] room_id={room_id}: 0 lessons today "
              f"(UTC window {day_start} .. {day_end}); "
              f"{len(other_dates)} lesson(s) exist in this room on other dates")
    else:
        print(f"[SCHEDULE] room_id={room_id}: returning {len(matched)} lesson(s)")

    lessons = []
    for lesson in matched:
        # start/end are naive UTC in the DB; attach UTC to get the true unix time.
        lessons.append(LessonResponse(
            name=lesson.name,
            start=int(lesson.start.replace(tzinfo=timezone.utc).timestamp()),
            end=int(lesson.end.replace(tzinfo=timezone.utc).timestamp())
        ))
    return lessons


@private_router.get("/alarm", response_model=AlarmResponse,
                    status_code=status.HTTP_200_OK)
async def get_alarm(db: db_dependency, room_id: room_id_dependency,
                    current_alarm: bool):
    # Report the alarm state for this device's room. `ring` is True when the
    # state just changed, so the device plays the start/finish sound once.
    alarm = (await db.execute(
        select(Alarm).where(Alarm.room_id == room_id)
    )).scalar_one_or_none()
    is_alarm = bool(alarm.is_active) if alarm is not None else False
    return AlarmResponse(
        is_alarm=is_alarm,
        ring=current_alarm != is_alarm
    )


@private_router.post("/sensors", status_code=status.HTTP_201_CREATED)
async def send_sensors(db: db_dependency, room_id: room_id_dependency,
                       measure_obj: SensorsObj):
    obj = measure_obj.model_dump()
    obj["measure_time"] = datetime.fromtimestamp(
        obj.pop("measure_timestamp"),
        ZoneInfo("Europe/Kyiv")
    )
    new_measure = Measure(**obj, room_id=room_id)
    db.add(new_measure)
    await db.commit()


def iter_read_file(file_path: str | Path):
    with open(file_path, "rb") as f:
        yield from f


@private_router.get("/ringtone_old", status_code=status.HTTP_200_OK)
async def stream_ringtone(db: db_dependency, room_id: room_id_dependency,
                          settings: settings_dependency):
    query = select(Ringtone).where(Ringtone.room_id == room_id).order_by(Ringtone.created_at)
    result = await db.execute(query)
    ringtone = result.scalar_one_or_none()
    if ringtone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ringtone not found")

    ringtone_filename = settings.ringtones_path / ringtone.filename

    return StreamingResponse(iter_read_file(ringtone_filename), media_type="audio/mpeg")


@private_router.get("/ringtone_code", status_code=status.HTTP_200_OK)
async def get_ringtone_code(db: db_dependency, room_id: room_id_dependency):
    query = select(Ringtone).where(Ringtone.room_id == room_id).order_by(Ringtone.created_at)
    result = await db.execute(query)
    ringtone = result.scalar_one_or_none()
    if ringtone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ringtone not found")

    ringtone_code = "R" + ringtone.filename
    return RingtoneResponse(code=ringtone_code)


@private_router.get("/voice_messages", response_model=list[str],
                    status_code=status.HTTP_200_OK)
async def get_voice_messages(db: db_dependency, room_id: room_id_dependency):
    query = select(VoiceMessage).where(VoiceMessage.room_id == room_id).order_by(VoiceMessage.created_at)
    result = await db.execute(query)
    voice_messages = result.scalars().all()
    # Return a bare JSON list (the device expects a list, same as /schedule).
    # No voice messages -> empty list, not a 404.
    return ["V" + vm.filename for vm in voice_messages]


@private_router.post("/logs", status_code=status.HTTP_200_OK)
async def stream_ringtone(db: db_dependency, room_id: room_id_dependency,
                          settings: settings_dependency, logs: list[str]):
    log_fn = settings.ring_logs_path / f"{room_id}_{datetime.now().timestamp():.0f}.txt"
    with log_fn.open("w", encoding="utf-8") as f:
        f.writelines(l + "\n" for l in logs)
