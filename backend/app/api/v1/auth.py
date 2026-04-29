"""Auth routes — Google OAuth login and token refresh."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import get_or_create_user, issue_tokens, verify_google_id_token
from app.core.security import decode_token, create_access_token

router = APIRouter(prefix='/auth', tags=['auth'])


class GoogleLoginRequest(BaseModel):
    id_token: str  # Google OAuth ID token from frontend


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post('/login/google', response_model=TokenResponse)
async def google_login(body: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a Google ID token for ParaWorks JWT tokens."""
    try:
        claims = await verify_google_id_token(body.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    email = claims.get('email', '')
    name = claims.get('name', email)
    google_id = claims.get('sub', '')
    avatar_url = claims.get('picture')

    try:
        user, _ = await get_or_create_user(db, email=email, name=name, google_id=google_id, avatar_url=avatar_url)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account is deactivated')

    access_token, refresh_token = issue_tokens(user)
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post('/refresh', response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')

    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Malformed token')

    from sqlalchemy import select
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')

    access_token, new_refresh = issue_tokens(user)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)
