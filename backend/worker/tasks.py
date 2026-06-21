import asyncio
import logging
from worker.celery_app import celery_app
from app.db import async_session_maker, engine
from app.models.ticket import Ticket
from app.ai.classify import classify_ticket

logger = logging.getLogger(__name__)

async def _async_process_new_ticket(ticket_id: int):
    logger.info(f"Starting background async triage for ticket #{ticket_id}")

    try:
        # 1. Open async db session
        async with async_session_maker() as db:
            # 2. Fetch the ticket
            ticket = await db.get(Ticket, ticket_id)
            if not ticket:
                logger.error(f"Ticket #{ticket_id} not found in database!")
                return

            # 2. Run the classification using the oMLX server wrapper
            # We pass the ticket's subject and body
            classification = classify_ticket(ticket.subject, ticket.body)

            # 3. Update the ticket fields with the AI's findings
            ticket.priority = classification["priority"]
            ticket.category = classification["category"]
            ticket.sentiment = classification["sentiment"]

            # 4. Save and commit updates to Postgres
            await db.commit()
            logger.info(
                f"Ticket #{ticket_id} successfully triaged by LLM. "
                f"Category: {ticket.category}, Priority: {ticket.priority}, Sentiment: {ticket.sentiment}"
            )
    finally:
        # Crucial: Dispose of connection pool. This prevents connections
        # from being carried over to a different event loop in subsequent tasks.
        logger.info("Disposing databse connection pool for the task event loop.")
        await engine.dispose()

@celery_app.task(name="worker.tasks.process_new_ticket")
def process_new_ticket(ticket_id: int):
    """
    Synchronous celery entrypoint. Start and asyncio event loop
    to run the async database operation.
    """
    asyncio.run(_async_process_new_ticket(ticket_id))