from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from fastapi import HTTPException, status, APIRouter, Security
from pydantic import BaseModel, Field
from models import Measure
from routers.db_tools import db_dependency  # , api_key_header


class MeasureObj(BaseModel):
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity: Optional[float] = Field(None, description="Humidity in %")
    volume: Optional[float] = Field(None, description="Room noise volume in dB")
    air_quality: Optional[float] = Field(None, description="CO2 concentration in %")
    measure_timestamp: Optional[int] = Field(None, description="Timestamp")


measures_router = APIRouter(
    prefix="/{room_id}/measures",
    tags=["rooms", "measures"]
)


@measures_router.get("/", status_code=status.HTTP_200_OK)
async def read_all_measures_by_room(db: db_dependency, room_id: int):
    query = select(Measure).where(Measure.room_id == room_id)
    result = await db.execute(query)
    return result.scalars().all()


@measures_router.get("/{measure_id}", status_code=status.HTTP_200_OK)
async def read_measure_by_id(db: db_dependency, room_id: int, measure_id: int):
    query = select(Measure).where((Measure.id == measure_id) & (Measure.room_id == room_id))
    result = await db.execute(query)
    measure = result.scalar_one_or_none()
    if measure is not None:
        return measure
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measure not found")


@measures_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_measure(db: db_dependency, measure_obj: MeasureObj, room_id: int):
    obj = measure_obj.model_dump()
    obj["measure_time"] = datetime.fromtimestamp(
        obj.pop("measure_timestamp"),
        ZoneInfo("Europe/Kyiv")
    )
    new_measure = Measure(**obj, room_id=room_id)
    db.add(new_measure)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No such room")


@measures_router.post("/{measure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_measure_by_id(db: db_dependency, measure_obj: MeasureObj, room_id: int, measure_id: int):
    query = select(Measure).where((Measure.id == measure_id) & (Measure.room_id == room_id))
    result = await db.execute(query)
    measure = result.scalar_one_or_none()
    if measure is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measure not found")

    measure.temperature = measure_obj.temperature
    measure.humidity = measure_obj.humidity
    measure.volume = measure_obj.volume
    measure.air_quality = measure_obj.air_quality
    measure.measure_time = datetime.fromtimestamp(
        measure.measure_timestamp,
        ZoneInfo("Europe/Kyiv")
    )

    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No such room")


@measures_router.delete("/{measure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_measure_by_id(db: db_dependency, room_id: int, measure_id: int):
    query = select(Measure).where((Measure.id == measure_id) & (Measure.room_id == room_id))
    result = await db.execute(query)
    measure = result.scalar_one_or_none()
    if measure is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measure not found")
    await db.delete(measure)
    await db.commit()
