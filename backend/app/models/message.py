from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .ticket import Ticket
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #CASCADE if the ticket is deleted, its thread messages are deleted automatically
    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('tickets.id', ondelete="CASCADE"),
        nullable=False,
        index=True # Index to speed up loading threads
    )
    sender_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal_note: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="messages")