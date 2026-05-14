from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from fastapi import HTTPException, status, APIRouter
from pydantic import BaseModel
from models import Lesson
from routers.db_tools import db_dependency


class LessonObj(BaseModel):
    name: str
    start: datetime
    end: datetime
    room_id: int


lessons_router = APIRouter(
    prefix="/lessons",
    tags=["lessons"]
)


@lessons_router.get("/", status_code=status.HTTP_200_OK)
async def read_all_lessons(db: db_dependency):
    query = select(Lesson)
    result = await db.execute(query)
    return result.scalars().all()


@lessons_router.get("/{lesson_id}", status_code=status.HTTP_200_OK)
async def read_lesson_by_id(db: db_dependency, lesson_id: int):
    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    if lesson is not None:
        return lesson
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")


@lessons_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_lesson(db: db_dependency, lesson_obj: LessonObj):
    query = select(Lesson).where((Lesson.start.between(lesson_obj.start, lesson_obj.end) |
                                 Lesson.end.between(lesson_obj.start, lesson_obj.end) |
                                 ((Lesson.start > lesson_obj.start) & (Lesson.end < lesson_obj.end))) &
                                 (Lesson.room_id == lesson_obj.room_id))
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    if lesson is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ths lesson is overlapping with another lesson {lesson.room_id}")

    new_lesson = Lesson(**lesson_obj.model_dump())
    db.add(new_lesson)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No such room")


@lessons_router.post("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_lesson_by_id(db: db_dependency, lesson_obj: LessonObj, lesson_id: int):
    query = select(Lesson).where((Lesson.start.betweet(lesson_obj.start, lesson_obj.end) |
                                 Lesson.end.betweet(lesson_obj.start, lesson_obj.end) |
                                 ((Lesson.start > lesson_obj.start) & (Lesson.end < lesson_obj.end))) &
                                 (Lesson.room_id == lesson_obj.room_id))
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    if lesson is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ths lesson is overlapping with another lesson {lesson.room_id}")

    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    lesson.name = lesson_obj.name
    lesson.start = lesson_obj.start
    lesson.end = lesson_obj.end
    lesson.room_id = lesson_obj.room_id

    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No such room")


@lessons_router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson_by_id(db: db_dependency, lesson_id: int):
    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(query)
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    await db.delete(lesson)
    await db.commit()
