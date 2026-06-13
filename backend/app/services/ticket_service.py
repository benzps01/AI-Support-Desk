from datetime import datetime, timezone
from typing import Optional, Sequence
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket
from app.models.message import TicketMessage
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.schemas.message import MessageCreate

class TicketService:
    @staticmethod
    async def create_ticket(db: AsyncSession, user: User, ticket_in: TicketCreate) -> Ticket:
        db_ticket = Ticket(
            org_id=user.org_id,
            customer_id=user.id,
            subject=ticket_in.subject,
            body=ticket_in.body,
            status="open"
        )
        db.add(db_ticket)
        await db.commit()
        await db.refresh(db_ticket)
        return db_ticket

    @staticmethod
    async def get_tickets(
        db: AsyncSession,
        user: User,
        status_filter: Optional[str] = None
    ) -> Sequence[Ticket]:
        """Fetch All tickets scoped to the active tenant and user role"""
        filters = [Ticket.org_id == user.org_id]

        if user.role == "customer":
            filters.append(Ticket.customer_id == user.id)

        if status_filter:
            filters.append(Ticket.status == status_filter)

        query = select(Ticket).where(and_(*filters)).order_by(Ticket.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_ticket(db: AsyncSession, user: User, ticket_id: int) -> Ticket:
        query = select(Ticket).options(
            selectinload(Ticket.messages)
        ).where(Ticket.id == ticket_id)

        result = await db.execute(query)
        ticket = result.scalars().first()

        # Enforce multi-tenant organization boundary
        if not ticket or ticket.org_id != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Enforce user role boundary
        if user.role == "customer" and ticket.customer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )

        return ticket

    
    @staticmethod
    async def update_ticket(
        db: AsyncSession,
        user: User,
        ticket_id: int,
        ticket_update: TicketUpdate
    ) -> Ticket:
        """ Update ticket details (status or assignment), restricted to agents and admins."""
        # This is auto-enforce organization security boundary checks
        ticket = await TicketService.get_ticket(db, user, ticket_id)

        if user.role not in ["agent", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )

        # Appy status updates
        if ticket_update.status is not None:
            ticket.status = ticket_update.status
            if ticket_update.status == "resolved":
                ticket.resolved_at = datetime.now(timezone.utc)
            else:
                ticket.resolved_at = None

        # Apply assignment updates
        if ticket_update.assigned_agent_id is not None:
            # Verify the assigned agent belongs to the same organization
            agent_query = select(User).where(
                and_(User.id == ticket_update.assigned_agent_id, User.org_id == user.org_id)
            )
            agent_results = await db.execute(agent_query)
            agent = agent_results.scalars().first()
            if not agent or agent.role not in ["agent", "admint"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid agent assignment"
                )
            ticket.assigned_agent_id = ticket_update.assigned_agent_id

        await db.commit()
        await db.refresh(ticket)
        return ticket


    @staticmethod
    async def create_message(
        db: AsyncSession,
        user: User,
        ticket_id: int,
        message_in: MessageCreate
    ) -> TicketMessage:
        """Create a new message on a ticket, enforcing access controls."""
        #Authenticate that user has access to this ticket
        ticket = await TicketService.get_ticket(db, user, ticket_id)

        # Customers cannot write internal notes
        if message_in.is_internal_note and user.role not in ["agent", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers cannot post internal notes"
            )

        db_message = TicketMessage(
            ticket_id=ticket.id,
            sender_id=user.id,
            body=message_in.body,
            is_internal_note=message_in.is_internal_note
        )
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)
        return db_message

    