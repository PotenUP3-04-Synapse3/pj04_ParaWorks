from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from sqlalchemy import select

from backend.core.config import settings
from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.user import User
from backend.schemas.auth import LoginRequest, LoginResponse, UserRead

log = structlog.get_logger(__name__)
router = APIRouter(prefix='/auth', tags=['auth'])



def _create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {'sub': user_id, 'exp': expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


@router.post('/login', response_model=LoginResponse)
async def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    result = await db.execute(select(User).where(User.email == payload.email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='이메일 또는 비밀번호가 올바르지 않습니다')
    if not bcrypt.checkpw(payload.password.encode(), user.hashed_password.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='이메일 또는 비밀번호가 올바르지 않습니다')

    token = _create_token(user.id)
    log.info('auth.login', user_id=user.id)
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))


@router.get('/me', response_model=UserRead)
async def me(db: DbSession, user_id: CurrentUserId) -> UserRead:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return UserRead.model_validate(user)
