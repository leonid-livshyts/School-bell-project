from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# CORS: allow the Vite dev server, Coder wildcard subdomains, and any https
# origin (covers the prod deploy domain). allow_credentials=True is required
# so the Authorization: Bearer header is allowed cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^http://localhost:5173$"
        r"|^https://[a-zA-Z0-9-]+--main--[a-zA-Z0-9-]+--[a-zA-Z0-9-]+\.coder\.brobots\.org\.ua$"
        r"|^https://[a-zA-Z0-9.-]+$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

