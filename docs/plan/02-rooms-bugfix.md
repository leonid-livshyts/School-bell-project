# Step 2 — Fix the broken UPDATE and DELETE handlers in `rooms.py`

## Goal
`POST /rooms/{room_id}` and `DELETE /rooms/{room_id}` currently 500 (or worse,
silently misbehave) because the handlers query the wrong table and reference
fields that don't exist on the request model. Make them actually update and
delete rooms.

## Why this is step 2
The frontend's Rooms page (step 7) needs working CRUD. Leaving these endpoints
broken would force the UI to either hide functionality or display fake success
states. One small surgical fix unlocks the whole page.

## What's wrong today

`backend/routers/rooms.py`:

```python
@rooms_router.post("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_lesson_by_id(db: db_dependency, room_obj: RoomObj, room_id: int):
    query = select(Lesson).where(Lesson.id == room_id)   # ← wrong table
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(...)
    room.name = room_obj.name
    room.start = room_obj.start                          # ← Room has no .start
    room.end = room_obj.end                              # ← Room has no .end
    await db.commit()
```

```python
@rooms_router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_by_id(db: db_dependency, room_id: int):
    query = select(Lesson).where(Lesson.id == room_id)   # ← wrong table
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    ...
```

Three bugs:
1. **Wrong model.** Both handlers select from `Lesson`, not `Room`. The right
   row is never found.
2. **Wrong handler name.** `update_lesson_by_id` is the function name in the
   rooms router — confusing but not user-visible. Rename to `update_room_by_id`.
3. **Nonexistent fields.** `RoomObj` only has `name`. The update assigns
   `room.start` and `room.end`, neither of which exists on the `Room` model
   (see `backend/models.py:39`).

## Files affected
- `backend/routers/rooms.py` — surgical edits to two handlers.
- No model changes. No new files.

## Detailed change

Replace the broken handlers with:

```python
@rooms_router.post("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_room_by_id(db: db_dependency, room_obj: RoomObj, room_id: int):
    query = select(Room).where(Room.id == room_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    room.name = room_obj.name

    try:
        await db.commit()
    except IntegrityError as ie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A room with this name already exists",
        ) from ie


@rooms_router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_by_id(db: db_dependency, room_id: int):
    query = select(Room).where(Room.id == room_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.delete(room)
    await db.commit()
```

### Cascade behaviour
`Room` is referenced by `Lesson.room_id`, `Measure.room_id`, `Alarm.room_id`,
`Device.room_id`, `VoiceMessage.room_id`, `Ringtone.room_id`. The SQLAlchemy
models do **not** declare `ondelete="CASCADE"`. SQLite with
`PRAGMA foreign_keys=ON` (set in `database.py`) will therefore reject the
delete with an `IntegrityError` whenever any child row still references the
room.

We will **not** add cascades in this step. That is a model change with data
implications and is out of the surgical scope. Instead, the handler catches
`IntegrityError` and returns a 409 telling the caller to delete dependents
first. Add an explicit catch:

```python
    try:
        await db.delete(room)
        await db.commit()
    except IntegrityError as ie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is still referenced by lessons/devices/measures/etc.",
        ) from ie
```

The frontend will surface this 409 as a clear toast on the Rooms page.

## Verification

```bash
# Pre-step: log in to get a bearer token (rooms router requires oauth2).
TOKEN=$(curl -s -X POST http://localhost:8080/login \
  -d "username=admin&password=admin" | jq -r .access_token)
H="Authorization: Bearer $TOKEN"

# Create
curl -i -X POST http://localhost:8080/rooms/ \
  -H "$H" -H "Content-Type: application/json" \
  -d '{"name":"TEST_ROOM"}'                        # expect 201

# Read
ID=$(curl -s http://localhost:8080/rooms/ -H "$H" \
  | jq '.[] | select(.name=="TEST_ROOM") | .id')

# Update
curl -i -X POST http://localhost:8080/rooms/$ID \
  -H "$H" -H "Content-Type: application/json" \
  -d '{"name":"TEST_ROOM_RENAMED"}'                # expect 204

# Delete (no children → success)
curl -i -X DELETE http://localhost:8080/rooms/$ID \
  -H "$H"                                          # expect 204

# Delete (with children → 409)
# Create a room, attach a lesson to it, then try to delete the room.
# Should get 409 with the "still referenced" detail.
```

## Risks and edge cases
- **Renaming the handler function** (`update_lesson_by_id` → `update_room_by_id`)
  changes the OpenAPI `operationId`. Anything that depends on the exact
  operationId (none currently) would need updating.
- **409 on delete with children** is intentional. The frontend must understand
  this status code (it will, see step 7 Rooms page).
- **No data migration.** The schema is unchanged; existing rows are unaffected.

## Done when
- Both handlers query `Room`, not `Lesson`.
- `update_room_by_id` only assigns `name` (no nonexistent fields).
- `delete_room_by_id` catches `IntegrityError` → 409.
- All four curl checks above pass.

## Commit
```
backend: fix rooms update/delete to actually query Room

Both handlers were querying Lesson and the update wrote to fields
(start/end) that don't exist on Room. Rename update_lesson_by_id ->
update_room_by_id; only assign `name`. Translate FK-constraint
IntegrityError on delete into a 409 with a clear message.
```
