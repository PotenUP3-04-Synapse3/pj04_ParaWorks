from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.core.demo_auth import (
    DemoUser,
    authenticate_demo_user,
    get_demo_user,
    list_demo_users,
    require_admin_user,
    serialize_demo_user,
)

router = APIRouter(prefix='/auth', tags=['auth'])
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]
AdminUser = Annotated[DemoUser, Depends(require_admin_user)]


class LoginRequest(BaseModel):
    email: str


@router.get('/me')
def get_current_user(user: CurrentUser) -> dict:
    return {'user': serialize_demo_user(user)}


@router.get('/login-options')
def get_login_options() -> dict:
    return {'users': list_demo_users()}


@router.post('/login')
def login(request: LoginRequest) -> dict:
    return {'user': serialize_demo_user(authenticate_demo_user(request.email))}


@router.get('/users')
def get_users(_: AdminUser) -> dict:
    return {'users': list_demo_users()}
