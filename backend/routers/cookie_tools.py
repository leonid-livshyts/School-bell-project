from typing import Annotated
from fastapi import Cookie
from pydantic import BaseModel


class Cookies(BaseModel):
    model_config = {"extra": "forbid"}

    session: str | None = None


cookie_dependency = Annotated[Cookies, Cookie()]