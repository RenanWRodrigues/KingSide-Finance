"""FastAPI dependency for JWT authentication."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.core.security import decode_access_token

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class CurrentUser(BaseModel):
    sub: str


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
) -> CurrentUser:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        sub: str | None = payload.get("sub")
        if not sub:
            raise credentials_exc
    except ValueError:
        raise credentials_exc
    return CurrentUser(sub=sub)
