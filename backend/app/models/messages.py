from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class MessageChannel(Base):
    __tablename__ = 'message_channels'

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500))
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    messages: Mapped[list['Message']] = relationship(back_populates='channel')


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey('message_channels.id'), index=True)
    author_name: Mapped[str] = mapped_column(String(120))
    author_role: Mapped[str] = mapped_column(String(80))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    channel: Mapped[MessageChannel] = relationship(back_populates='messages')
