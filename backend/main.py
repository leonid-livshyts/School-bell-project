from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from database import engine
from models import Base
from routers import lessons, rooms, measures, devices, voice_messages, ringtones, private, authentication, alarms
from config import get_settings


async def init_models():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_models()
    yield


settings = get_settings()
settings.init_fs()
app = FastAPI(debug=True, lifespan=lifespan, title=settings.app_name)


app.include_router(authentication.auth_router)
app.include_router(lessons.lessons_router)
rooms.rooms_router.include_router(measures.measures_router)
app.include_router(rooms.rooms_router)
app.include_router(devices.devices_router)
app.include_router(voice_messages.voice_messages_router)
app.include_router(ringtones.ringtones_router)
app.include_router(private.private_router)
app.include_router(alarms.alarms_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")

