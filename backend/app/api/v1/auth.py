from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.demo_auth import (
    DemoUser,
    authenticate_demo_user,
    get_demo_user,
    list_demo_users,
    require_admin_user,
    serialize_demo_user,
)
from backend.app.core.session_auth import (
    clear_auth_cookies,
    issue_auth_cookies,
    revoke_refresh_token_family,
    rotate_refresh_token,
    serialize_auth_user,
    upsert_auth_user_from_demo,
)
from backend.app.db.session import get_db

router = APIRouter(prefix='/auth', tags=['auth'])
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]
AdminUser = Annotated[DemoUser, Depends(require_admin_user)]
DbSession = Annotated[Session, Depends(get_db)]


class LoginRequest(BaseModel):
    email: str


@router.get('/me')
def get_current_user(user: CurrentUser) -> dict:
    return {'user': serialize_demo_user(user)}


@router.get('/login-options')
def get_login_options() -> dict:
    return {'users': list_demo_users()}


@router.post('/login')
def login(request: LoginRequest, response: Response, db: DbSession) -> dict:
    demo_user = authenticate_demo_user(request.email)
    auth_user = upsert_auth_user_from_demo(db, demo_user)
    issue_auth_cookies(response, db, auth_user)
    db.commit()
    return {'user': serialize_auth_user(auth_user)}


@router.post('/refresh')
def refresh(request: Request, response: Response, db: DbSession) -> dict:
    settings = get_settings()
    auth_user = rotate_refresh_token(response, db, request.cookies.get(settings.auth_refresh_cookie_name), settings)
    if auth_user is None:
        raise HTTPException(status_code=401, detail='Refresh token is invalid or expired.')
    db.commit()
    return {'user': serialize_auth_user(auth_user)}


@router.post('/logout')
def logout(request: Request, response: Response, db: DbSession) -> dict:
    settings = get_settings()
    revoke_refresh_token_family(db, request.cookies.get(settings.auth_refresh_cookie_name))
    clear_auth_cookies(response, settings)
    db.commit()
    return {'status': 'logged_out'}


@router.get('/users')
def get_users(_: AdminUser) -> dict:
    return {'users': list_demo_users()}
