from typing import Optional, Annotated, Union
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, APIRouter, File, UploadFile, Form, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from models import Ringtone
from routers.db_tools import db_dependency
from routers.oauth_tools import oauth2
from config import settings_dependency


class RingtoneObj(BaseModel):
    filename: str
    room_id: Optional[int]


ringtones_router = APIRouter(
    prefix="/ringtones",
    tags=["ringtones"],
    dependencies=[Depends(oauth2)],
)


@ringtones_router.get("/", status_code=status.HTTP_200_OK)
async def read_all_ringtones(db: db_dependency):
    query = select(Ringtone)
    result = await db.execute(query)
    return result.scalars().all()


@ringtones_router.get("/{ringtone_id}", status_code=status.HTTP_200_OK)
async def read_ringtone_by_id(db: db_dependency, ringtone_id: int):
    query = select(Ringtone).where(Ringtone.id == ringtone_id)
    result = await db.execute(query)
    ringtone = result.scalar_one_or_none()
    if ringtone is not None:
        return ringtone
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice Message not found")


@ringtones_router.get("/{ringtone_id}/download", status_code=status.HTTP_200_OK,
                      response_class=FileResponse)
async def download_ringtone_by_id(db: db_dependency, settings: settings_dependency,
                                  ringtone_id: int):
    query = select(Ringtone).where(Ringtone.id == ringtone_id)
    result = await db.execute(query)
    ringtone = result.scalar_one_or_none()
    if ringtone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ringtone not found")

    return settings.ringtones_path / ringtone.filename


@ringtones_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_ringtone(db: db_dependency, settings: settings_dependency,
                          file: Annotated[UploadFile, File()],
                          room_id: Union[int, None] = Form(default=None)):
    ringtone_path = (settings.ringtones_path /
                     f"{datetime.now().timestamp() * 1000:.0f}_{file.filename}")
    with ringtone_path.open("wb") as f:
        f.write(await file.read())

    new_ringtone = Ringtone(
        filename=ringtone_path.name,
        room_id=room_id
    )
    db.add(new_ringtone)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ringtone not found")


@ringtones_router.delete("/{ringtone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ringtone_by_id(db: db_dependency, settings: settings_dependency, ringtone_id: int):
    query = select(Ringtone).where(Ringtone.id == ringtone_id)
    result = await db.execute(query)
    ringtone = result.scalar_one_or_none()
    if ringtone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ringtone not found")

    ringtone_path = settings.ringtones_path / ringtone.filename
    if ringtone_path.is_file():
        ringtone_path.unlink(missing_ok=True)

    await db.delete(ringtone)
    await db.commit()
