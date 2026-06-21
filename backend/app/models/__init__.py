from app.db import Base
from app.models.organization import Organization
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import TicketMessage
from app.models.embedding import TicketEmbedding
from app.models.suggestion import AISuggestion

# Expose everything to make Alembic imports cleaner
__all__ = ["Base", "Organization", "User", "Ticket", "TicketMessage", "TicketEmbedding", "AISuggestion"]