"""Auth service — Google OAuth, domain enforcement, JWT issuance."""
from __future__ import annotations

import logging
from typing import Optional, Tuple
from uuid import UUID

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token,
    encrypt_token, decrypt_token,
)
from app.models.organization import Organization
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


async def verify_google_id_token(token: str) -> dict:
    """Verify a Google ID token and return its claims."""
    try:
        claims = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        return claims
    except Exception as exc:
        logger.warning('Invalid Google ID token: %s', exc, exc_info=True)
        raise ValueError(f'Invalid Google ID token: {exc}')


async def get_or_create_user(
    db: AsyncSession,
    email: str,
    name: str,
    google_id: str,
    avatar_url: Optional[str],
) -> Tuple[User, bool]:
    """
    Get existing user or create a new one.
    Enforces company domain restriction.
    Returns (user, created_flag).
    """
    allowed_domains = settings.allowed_email_domains_list
    domain = email.split('@')[-1].lower() if '@' in email else ''

    if allowed_domains and domain not in allowed_domains:
        raise PermissionError(f'Email domain @{domain} is not allowed')

    # Look up existing user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # Update google_id if missing
        if not user.google_id:
            user.google_id = google_id
        return user, False

    # Create org if first user of this domain
    org_result = await db.execute(
        select(Organization).where(Organization.domain == domain)
    )
    org = org_result.scalar_one_or_none()

    if not org:
        org = Organization(
            name=domain,
            domain=domain,
            settings='{}',
        )
        db.add(org)
        await db.flush()

    user = User(
        email=email,
        name=name,
        google_id=google_id,
        avatar_url=avatar_url,
        role=UserRole.member,
        is_active=True,
        organization_id=org.id,
    )
    db.add(user)
    await db.flush()

    return user, True


def issue_tokens(user: User) -> Tuple[str, str]:
    """Issue access and refresh JWT tokens for a user."""
    payload = {
        'sub': str(user.id),
        'org_id': str(user.organization_id),
        'role': user.role.value,
    }
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token({'sub': str(user.id)})
    return access_token, refresh_token
