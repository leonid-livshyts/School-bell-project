from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy import event
from config import get_settings


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

settings = get_settings()
DB_URL = f"sqlite+aiosqlite:///{settings.database_path}/app.db"
engine = create_async_engine(DB_URL)
SessionLocal = async_sessionmaker(bind=engine)
