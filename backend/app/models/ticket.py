from __future__ import annotations
from time import timezone
from datetime import datetime
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .message import TicketMessage
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True # Index to speed up "my tickets"
    )
    assigned_agent_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"), # SET NULL so that deleting an agent account doesn't destroy the ticket history
        nullable=True,
        index=True # Index to speed up "my queue" agent views
    )

    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default="open"   # 'open', 'in_progress', 'resolved', 'closed'
    )

    # AI Enrichment fields
    priority: Mapped[Optional[str]] = mapped_column(String, nullable=True) # 'low', 'medium', 'high', 'urgent'
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    sla_due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    messages: Mapped[list[TicketMessage]] = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_tickets_org_status", "org_id", "status"),
    )