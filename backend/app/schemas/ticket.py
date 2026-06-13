from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.message import MessageResponse

class TicketCreate(BaseModel):
    subject: str
    body: str

class TicketUpdate(BaseModel):
    status: Optional[str] = None
    assigned_agent_id: Optional[int] = None

class TicketResponse(BaseModel):
    id: int
    org_id: int
    customer_id: int
    assigned_agent_id: Optional[int]
    subject: str
    body: str
    status: str
    priority: Optional[str]
    category: Optional[str]
    sentiment: Optional[str]
    sla_due_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

class TicketDetailResponse(TicketResponse):
    messages: list[MessageResponse] = []