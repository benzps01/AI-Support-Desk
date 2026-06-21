from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from worker.tasks import process_new_ticket

from app.deps import get_db, get_current_user, RoleChecker
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketResponse, TicketDetailResponse, TicketUpdate
from app.schemas.message import MessageCreate, MessageResponse
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_in: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new ticket. Available to all roles."""
    ticket = await TicketService.create_ticket(db, current_user, ticket_in)

    # Dispatch bg celery task
    #.delay() puts the job in Redis instead of running it synchonously
    process_new_ticket.delay(ticket.id)

    return ticket

@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    status: Optional[str] = Query(None, pattern="^(open|in_progress|resolved|closed)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """list tickets for the user's organization. Scoped by role permission."""
    return await TicketService.get_tickets(db, current_user, status)


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific ticket and its message thread."""
    return await TicketService.get_ticket(db, current_user, ticket_id)

@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    current_user: User = Depends(RoleChecker(["agent", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Update a ticket's assignment or status. Restricted to agents and admins"""
    return await TicketService.update_ticket(db, current_user, ticket_id, ticket_update)

@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def post_message(
    ticket_id: int,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Post a new message/reply on a ticket"""
    return await TicketService.create_message(db, current_user, ticket_id, message_in)

@router.get("/{ticket_id}/similar", response_model=list[TicketResponse])
async def get_similar_tickets(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top semantically similar resolved tickets to assist the agent.
    Available to all roles (usually used by agents in the AI Panel).
    """
    return await TicketService.get_similar_resolved_tickets(db, current_user, ticket_id)