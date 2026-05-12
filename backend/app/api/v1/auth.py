from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.google_identity import (
    GOOGLE_IDENTITY_SCOPES,
    GoogleIdentityError,
    build_google_identity_login_url,
    complete_google_identity_login,
    google_identity_missing_config,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_auth import (
    DemoUser,
    authenticate_demo_user,
    get_demo_user,
    list_demo_users,
    require_admin_user,
    serialize_demo_user,
)
from backend.app.core.rate_limit import rate_limit_auth
from backend.app.core.session_auth import (
    clear_auth_cookies,
    issue_auth_cookies,
    revoke_refresh_token_family,
    rotate_refresh_token,
    serialize_auth_user,
    upsert_auth_user_from_demo,
)
from backend.app.db.session import get_db
from backend.app.models import AuthUser
from backend.app.seeds.auth_users import seed_auth_users

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
    settings = get_settings()
    if not settings.paraworks_demo_mode:
        return {'users': []}
    return {'users': list_demo_users()}


@router.post('/login', dependencies=[Depends(rate_limit_auth)])
def login(request: LoginRequest, response: Response, db: DbSession) -> dict:
    settings = get_settings()
    if settings.paraworks_demo_mode:
        demo_user = authenticate_demo_user(request.email)
        auth_user = upsert_auth_user_from_demo(db, demo_user)
    elif settings.paraworks_env == 'local':
        auth_user = _authenticate_local_seed_user(db, request.email)
    else:
        raise HTTPException(status_code=403, detail='Demo login is disabled.')
    issue_auth_cookies(response, db, auth_user)
    db.commit()
    return {'user': serialize_auth_user(auth_user)}


@router.get('/google/login-url')
def get_google_login_url(settings: Annotated[Settings, Depends(get_settings)]) -> dict:
    missing_config = google_identity_missing_config(settings)
    if missing_config:
        return {
            'configured': False,
            'login_url': None,
            'state': None,
            'required_scopes': list(GOOGLE_IDENTITY_SCOPES),
            'redirect_uri': settings.google_identity_redirect_uri,
            'missing_config': missing_config,
        }
    try:
        login_url = build_google_identity_login_url(settings=settings)
    except GoogleIdentityError:
        return {
            'configured': False,
            'login_url': None,
            'state': None,
            'required_scopes': list(GOOGLE_IDENTITY_SCOPES),
            'redirect_uri': settings.google_identity_redirect_uri,
            'missing_config': ['GOOGLE_IDENTITY_CONFIGURATION'],
        }
    return {
        'configured': login_url.configured,
        'login_url': login_url.login_url,
        'state': login_url.state,
        'required_scopes': login_url.required_scopes,
        'redirect_uri': login_url.redirect_uri,
        'missing_config': login_url.missing_config,
    }


@router.get('/google/callback')
def google_login_callback(
    code: str,
    state: str,
    response: Response,
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        auth_user = complete_google_identity_login(
            db=db,
            settings=settings,
            response=response,
            code=code,
            state=state,
            cookie_issuer=issue_auth_cookies,
        )
    except GoogleIdentityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {'user': serialize_auth_user(auth_user)}


@router.post('/refresh', dependencies=[Depends(rate_limit_auth)])
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


def _authenticate_local_seed_user(db: Session, email: str) -> AuthUser:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=401, detail='Account not found.')

    seed_auth_users(db)
    auth_user = db.scalar(select(AuthUser).where(AuthUser.email == normalized_email))
    if auth_user is None or auth_user.status != 'active':
        raise HTTPException(status_code=401, detail='Account not found.')
    return auth_user
