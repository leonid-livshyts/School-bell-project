from functools import lru_cache
from typing import Annotated
from pathlib import Path
from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict

root_path = Path(__name__).resolve().parent

class Settings(BaseSettings):
    app_name: str = "Ring proj"
    voices_path: Path = root_path / "voices"
    ringtones_path: Path = root_path / "ringtones"
    ring_logs_path: Path = root_path / "ring_logs"
    database_path: Path = root_path / "db"

    model_config = SettingsConfigDict(env_file=".env")

    def init_fs(self):
        self.voices_path.mkdir(exist_ok=True)
        self.ringtones_path.mkdir(exist_ok=True)
        self.ring_logs_path.mkdir(exist_ok=True)
        self.database_path.mkdir(exist_ok=True)

@lru_cache
def get_settings():
    return Settings()


settings_dependency = Annotated[Settings, Depends(get_settings)]
