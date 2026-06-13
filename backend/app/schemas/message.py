from datetime import datetime
from pydantic import BaseModel

class MessageCreate(BaseModel):
    body: str
    is_internal_note: bool = False

class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    body: str
    is_internal_note: bool
    created_at: datetime

    class Config:
        from_attributes = True