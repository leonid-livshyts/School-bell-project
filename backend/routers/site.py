from fastapi import HTTPException, File, UploadFile, APIRouter, status, Depends
from routers.security import get_user_id
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from models import Room, Measure, Ringtone, VoiceMessage
from routers.db_tools import db_dependency
from config import settings_dependency
from datetime import datetime
from pydantic import BaseModel
from typing import Annotated

site_router = APIRouter(
    prefix="/site",
    tags=["site"] #,
    # dependencies=[Depends(get_user_id)]
)


class VoiceObj(BaseModel):
    voice: Annotated[UploadFile, File()]
    place: str


BELL_IDS = [
    "201_1", "201_2", "202", "204", "205", "206", "207",
    "208", "209", "210", "211_1", "211_2", "212",
    "MSL", "MHL"
]
last_uploaded_melody = {
    "201_1": "",
    "201_2": "",
    "202": "",
    "204": "",
    "205": "",
    "206": "",
    "207": "",
    "208": "",
    "209": "",
    "210": "",
    "211_1": "",
    "211_2": "",
    "212": "",
    "MHL": "",
    "MSL": ""
}


@site_router.get("/get_last_melody/{bell_id}")
async def get_last_melody(bell_id: str):
    return {"last_uploaded_melody": last_uploaded_melody[bell_id]}


@site_router.get("/get_sensor_data/{bell_id}")
async def get_sensor_data(bell_id: str, db: db_dependency):
    res = select(Room.id).where(Room.name == bell_id)
    stmt = select(Measure).where(Measure.room_id.in_(res)).order_by(Measure.measure_time.asc()).limit(20)

    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        return {"labels": [], "temperature": [], "airQuality": [], "noise": [], "humidity": []}

    return {
        "labels": [record.measure_time.strftime("%H:%M:%S") for record in records],
        "temperature": [record.temperature for record in records],
        "airQuality": [record.air_quality for record in records],
        "noise": [record.volume for record in records],
        "humidity": [record.humidity for record in records],
    }


@site_router.post("/bells/upload_melody/{bell_id}")
async def upload_melody(db: db_dependency, settings: settings_dependency, bell_id: str, melody: UploadFile = File(...)):
    global last_uploaded_melody
    query = select(Room).where(Room.name == bell_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()

    if room is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not found")

    ringtone_path = (settings.ringtones_path /
                     f"{datetime.now().timestamp() * 1000:.0f}_{melody.filename}")
    with ringtone_path.open("wb") as f:
        f.write(await melody.read())

    new_ringtone_path = Ringtone(
        filename=ringtone_path.name,
        room_id=room.id
    )
    db.add(new_ringtone_path)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="room not found")

    last_uploaded_melody[bell_id] = melody.filename
    return {"message": "Мелодію оновлено успішно!", "last_uploaded_melody": last_uploaded_melody}


@site_router.post("/voices/names", response_model=list)
async def get_list_of_voices(db: db_dependency):
    query = select(VoiceMessage)
    result = await db.execute(query)
    voices = result.scalars().all()

    res = []
    for i in voices:
        res.append(i.filename)

    return res


@site_router.post("/voices/add/{place}", status_code=status.HTTP_200_OK)
async def create_voise(db: db_dependency, settings: settings_dependency, file: Annotated[UploadFile, File()], place: str):
    if place == "workshop":
        workshop = ["MHL", "MSL"]
        for room_name in workshop:
            query = select(Room).where(Room.name == room_name)
            result = await db.execute(query)
            room = result.scalar_one_or_none()

            if room is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not found")

            voice_message_path = (settings.voices_path /
                                  f"{datetime.now().timestamp() * 1000:.0f}_{file.filename}")
            with voice_message_path.open("wb") as f:
                f.write(await file.read())

            new_voice_message_path = VoiceMessage(
                filename=voice_message_path.name,
                room_id=room.id
            )
            db.add(new_voice_message_path)
            try:
                await db.commit()
            except IntegrityError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="room not found")

    elif place == "school":
        voice_message_path = (settings.voices_path /
                              f"{datetime.now().timestamp() * 1000:.0f}_{file.filename}")
        with voice_message_path.open("wb") as f:
            f.write(await file.read())

        new_voice_message_path = VoiceMessage(
            filename=voice_message_path.name,
            room_id=None
        )
        db.add(new_voice_message_path)
        try:
            await db.commit()
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="room not found")

    else:
        query = select(Room).where(Room.name == place)
        result = await db.execute(query)
        room = result.scalar_one_or_none()

        if room is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not found")

        voice_message_path = (settings.voices_path /
                              f"{datetime.now().timestamp() * 1000:.0f}_{file.filename}")
        with voice_message_path.open("wb") as f:
            f.write(await file.read())

        new_voice_message_path = VoiceMessage(
            filename=voice_message_path.name,
            room_id=room.id
        )
        db.add(new_voice_message_path)
        try:
            await db.commit()
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="room not found")

    return status.HTTP_200_OK
