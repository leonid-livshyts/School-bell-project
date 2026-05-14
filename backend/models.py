from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from routers.password_tools import check_password


class Base(DeclarativeBase):
    pass


class CreatedUpdatedModel:
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        server_default=func.now(),
        onupdate=func.now()
    )


class Lesson(CreatedUpdatedModel, Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    start: Mapped[datetime]
    end: Mapped[datetime]
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))


class Room(CreatedUpdatedModel, Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    measures: Mapped[list["Measure"]] = relationship()


class Measure(Base):
    __tablename__ = "measures"

    id: Mapped[int] = mapped_column(primary_key=True)
    temperature: Mapped[float]
    humidity: Mapped[float]
    volume: Mapped[float]
    air_quality: Mapped[float]
    measure_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        server_default=func.now()
    )
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))


class Device(CreatedUpdatedModel, Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str]
    version: Mapped[str]
    installed_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=None,
        server_default=func.now()
    )
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))


class VoiceMessage(CreatedUpdatedModel, Base):
    __tablename__ = "voice_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    room_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rooms.id"))


class Ringtone(CreatedUpdatedModel, Base):
    __tablename__ = "ringtones"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    room_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rooms.id"))


class User(CreatedUpdatedModel, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[bytes]
    email: Mapped[str] = mapped_column(unique=True)
    role: Mapped[Optional[str]] = mapped_column(default="user")

    @classmethod
    async def find_by_username(cls, db: AsyncSession, username: str):
        query = select(cls).where(cls.username == username)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def authenticate(cls, db: AsyncSession, username: str, password: str):
        user = await cls.find_by_username(db, username)
        if not user or not check_password(password, user.hashed_password):
            print(user, check_password(password, user.hashed_password))
            return False
        return user


class Session(CreatedUpdatedModel, Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str]
    expired_at: Mapped[datetime]
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))


