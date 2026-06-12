from __future__ import annotations
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True) #BigInteger = postgres BigSerial
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    users: Mapped[List[User]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan"
    )