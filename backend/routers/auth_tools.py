from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from fastapi import Depends

oauth2 = OAuth2PasswordBearer(tokenUrl="/login")
auth_dependency = Annotated[str, Depends(oauth2)]
