"""Authentication routes — issues JWT access tokens."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)

# Single admin account for development/demo.
# In production, replace with a real user repository query.
_ADMIN_USERNAME = "admin"
_ADMIN_PASSWORD_HASH = hash_password("admin123")


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@router.post(
    "/token",
    response_model=Token,
    summary="Obtain JWT access token",
    description=(
        "Exchange username + password for a Bearer token. "
        "Default dev credentials: `admin` / `admin123`."
    ),
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    if form_data.username != _ADMIN_USERNAME or not verify_password(
        form_data.password, _ADMIN_PASSWORD_HASH
    ):
        logger.warning("Failed login attempt", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=form_data.username)
    logger.info("Token issued", username=form_data.username)
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )
