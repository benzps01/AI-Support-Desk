from app.models import Ticket
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, ForeignKey, String, JSON, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False) # 'classification' or 'reply'
    content: Mapped[dict] = mapped_column(JSON, nullable=False) # Holds the raw JSON prediction
    model: Mapped[str] = mapped_column(String, nullable=False) # Model name (e.g. gemma-4-e4b-it-4bit)
    accepted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True) # Did the agent use the suggestion?
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    ) 

    #Relationship back to Ticket
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="suggestions")