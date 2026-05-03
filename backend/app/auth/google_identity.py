import base64
import hashlib
import hmac
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.demo_auth import find_demo_user
from backend.app.models import AuthUser

GOOGLE_IDENTITY_SCOPES = ['openid', 'email', 'profile']


@dataclass(frozen=True)
class GoogleIdentityState:
    nonce: str


@dataclass(frozen=True)
class GoogleIdentityLoginUrl:
    login_url: str
    state: str
    required_scopes: list[str]
    redirect_uri: str
    missing_config: list[str]
    configured: bool = True


@dataclass(frozen=True)
class GoogleIdentityAccess:
    subject: str
    email: str
    email_verified: bool
    name: str


class GoogleIdentityError(RuntimeError):
    pass


class GoogleIdentityStateSigner:
    def __init__(self, secret: str) -> None:
        self.secret = secret.encode('utf-8')

    def create(self, *, nonce: str | None = None) -> str:
        payload = {'nonce': nonce or secrets.token_urlsafe(18)}
        payload_token = _b64encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
        signature = _sign(payload_token, self.secret)
        return f'{payload_token}.{signature}'

    def validate(self, state: str) -> GoogleIdentityState:
        try:
            payload_token, signature = state.split('.', 1)
        except ValueError as exc:
            raise GoogleIdentityError('Google identity state is malformed') from exc

        expected = _sign(payload_token, self.secret)
        if not hmac.compare_digest(signature, expected):
            raise GoogleIdentityError('Google identity state signature is invalid')

        try:
            payload = json.loads(_b64decode(payload_token))
        except (ValueError, json.JSONDecodeError) as exc:
            raise GoogleIdentityError('Google identity state is malformed') from exc
        return GoogleIdentityState(nonce=str(payload['nonce']))


class GoogleIdentityClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        http_client: httpx.Client | None = None,
        token_url: str = 'https://oauth2.googleapis.com/token',
        userinfo_url: str = 'https://openidconnect.googleapis.com/v1/userinfo',
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self.token_url = token_url
        self.userinfo_url = userinfo_url

    def exchange_code(self, *, code: str, redirect_uri: str) -> GoogleIdentityAccess:
        response = self.http_client.post(
            self.token_url,
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            },
        )
        response.raise_for_status()
        token_payload = response.json()
        access_token = str(token_payload['access_token'])
        userinfo_response = self.http_client.get(
            self.userinfo_url,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
        return GoogleIdentityAccess(
            subject=str(userinfo.get('sub') or ''),
            email=str(userinfo.get('email') or ''),
            email_verified=bool(userinfo.get('email_verified')),
            name=str(userinfo.get('name') or userinfo.get('email') or 'Google User'),
        )


def build_google_identity_login_url(
    *,
    settings: Settings,
    nonce: str | None = None,
) -> GoogleIdentityLoginUrl:
    if not settings.google_client_id:
        raise GoogleIdentityError('GOOGLE_CLIENT_ID is required for Google identity login')

    state = GoogleIdentityStateSigner(settings.google_identity_state_secret).create(nonce=nonce)
    query = urlencode(
        {
            'client_id': settings.google_client_id,
            'redirect_uri': settings.google_identity_redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(GOOGLE_IDENTITY_SCOPES),
            'prompt': 'select_account',
            'state': state,
        }
    )
    return GoogleIdentityLoginUrl(
        login_url=f'https://accounts.google.com/o/oauth2/v2/auth?{query}',
        state=state,
        required_scopes=list(GOOGLE_IDENTITY_SCOPES),
        redirect_uri=settings.google_identity_redirect_uri,
        missing_config=[],
    )


def google_identity_missing_config(settings: Settings) -> list[str]:
    missing: list[str] = []
    if not settings.google_client_id:
        missing.append('GOOGLE_CLIENT_ID')
    if not settings.google_client_secret:
        missing.append('GOOGLE_CLIENT_SECRET')
    if not settings.google_identity_redirect_uri:
        missing.append('GOOGLE_IDENTITY_REDIRECT_URI')
    if not settings.google_identity_state_secret:
        missing.append('GOOGLE_IDENTITY_STATE_SECRET')
    return missing


def complete_google_identity_login(
    *,
    db: Session,
    settings: Settings,
    response: Response,
    code: str,
    state: str,
    access: GoogleIdentityAccess | None = None,
    cookie_issuer: Callable[[Response, Session, AuthUser, Settings | None], str],
) -> AuthUser:
    GoogleIdentityStateSigner(settings.google_identity_state_secret).validate(state)
    access_payload = access or _exchange_google_identity_code(settings=settings, code=code)
    auth_user = upsert_auth_user_from_google_identity(db, access_payload)
    cookie_issuer(response, db, auth_user, settings)
    db.commit()
    db.refresh(auth_user)
    return auth_user


def upsert_auth_user_from_google_identity(db: Session, access: GoogleIdentityAccess) -> AuthUser:
    email = access.email.strip().lower()
    if not access.email_verified:
        raise ValueError('Google email must be verified.')
    if not email:
        raise ValueError('Google email is required.')

    seed_user = find_demo_user(email)
    if seed_user is None:
        raise ValueError('Google account is not invited to ParaWorks.')

    auth_user = db.scalar(select(AuthUser).where(AuthUser.email == email))
    if auth_user is None:
        auth_user = AuthUser(
            external_id=access.subject or seed_user.id,
            email=email,
            display_name=access.name or seed_user.name,
            role=seed_user.role,
            department=seed_user.department,
            title=seed_user.title,
            status='active',
            permission_levels=sorted(seed_user.permission_levels),
        )
        db.add(auth_user)
    else:
        if auth_user.status != 'active':
            raise ValueError('ParaWorks account is inactive.')
        auth_user.external_id = access.subject or auth_user.external_id
        auth_user.display_name = access.name or auth_user.display_name
    db.flush()
    return auth_user


def _exchange_google_identity_code(*, settings: Settings, code: str) -> GoogleIdentityAccess:
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleIdentityError('Google client id and secret are required for identity callback exchange')
    return GoogleIdentityClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    ).exchange_code(code=code, redirect_uri=settings.google_identity_redirect_uri)


def _sign(payload_token: str, secret: bytes) -> str:
    digest = hmac.new(secret, payload_token.encode('ascii'), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def _b64decode(value: str) -> bytes:
    padded = value + ('=' * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode('ascii'))
