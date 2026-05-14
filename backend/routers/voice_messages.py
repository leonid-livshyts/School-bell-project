from typing import Optional, Annotated, Union
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, APIRouter, File, UploadFile, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from models import VoiceMessage
from routers.db_tools import db_dependency
from config import settings_dependency


class VoiceMessageObj(BaseModel):
    filename: str
    room_id: Optional[int]


voice_messages_router = APIRouter(
    prefix="/voice_messages",
    tags=["voice_messages"]
)


@voice_messages_router.get("/", status_code=status.HTTP_200_OK)
async def read_all_voice_messages(db: db_dependency):
    query = select(VoiceMessage)
    result = await db.execute(query)
    return result.scalars().all()


@voice_messages_router.get("/{voice_message_id}", status_code=status.HTTP_200_OK)
async def read_voice_message_by_id(db: db_dependency, voice_message_id: int):
    query = select(VoiceMessage).where(VoiceMessage.id == voice_message_id)
    result = await db.execute(query)
    voice_message = result.scalar_one_or_none()
    if voice_message is not None:
        return voice_message
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice Message not found")


@voice_messages_router.get("/{voice_message_id}/download", status_code=status.HTTP_200_OK,
                           response_class=FileResponse)
async def download_voice_message_by_id(db: db_dependency, settings: settings_dependency,
                                       voice_message_id: int):
    query = select(VoiceMessage).where(VoiceMessage.id == voice_message_id)
    result = await db.execute(query)
    voice_message = result.scalar_one_or_none()
    if voice_message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice Message not found")

    return settings.voices_path / voice_message.filename


@voice_messages_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_voice_message(db: db_dependency, settings: settings_dependency,
                               file: Annotated[UploadFile, File()],
                               room_id: Union[int, None] = Form(default=None)):
    voice_message_path = (settings.voices_path /
                          f"{datetime.now().timestamp() * 1000:.0f}_{file.filename}")
    with voice_message_path.open("wb") as f:
        f.write(await file.read())

    new_voice_message = VoiceMessage(
        filename=voice_message_path.name,
        room_id=room_id
    )
    db.add(new_voice_message)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room not found")


@voice_messages_router.delete("/{voice_message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_message_by_id(db: db_dependency, settings: settings_dependency,
                                     voice_message_id: int):
    query = select(VoiceMessage).where(VoiceMessage.id == voice_message_id)
    result = await db.execute(query)
    voice_message = result.scalar_one_or_none()
    if voice_message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice Message not found")

    voice_message_path = settings.voices_path / voice_message.filename
    if voice_message_path.is_file():
        voice_message_path.unlink(missing_ok=True)

    await db.delete(voice_message)
    await db.commit()

