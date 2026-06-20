import asyncio
import logging
from worker.celery_app import celery_app
from app.db import async_session_maker
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)

async def _async_process_new_ticket(ticket_id: int):
    logger.info(f"Starting background async triage for ticket #{ticket_id}")

    # 1. Open async db session
    async with async_session_maker() as db:
        # 2. Fetch the ticket
        ticket = await db.get(Ticket, ticket_id)
        if not ticket:
            logger.error(f"Ticket #{ticket_id} not found in database!")
            return

        # 3. Apply mock classification values for testing the connection
        ticket.priority = "low"
        ticket.category = "general"
        ticket.sentiment = "neutral"

        # 4. Save Updates
        await db.commit()
        logger.info(f"Ticket #{ticket_id} successfully triaged with mock values.")

@celery_app.task(name="worker.tasks.process_new_ticket")
def process_new_ticket(ticket_id: int):
    """
    Synchronous celery entrypoint. Start and asyncio event loop
    to run the async database operation.
    """
    asyncio.run(_async_process_new_ticket(ticket_id))