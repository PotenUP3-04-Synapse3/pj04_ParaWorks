from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
