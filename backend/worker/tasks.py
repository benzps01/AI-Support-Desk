import asyncio
import logging
from worker.celery_app import celery_app
from app.db import async_session_maker, engine
from app.config import settings
from app.models.ticket import Ticket
from app.models.user import User
from app.models.embedding import TicketEmbedding
from app.models.suggestion import AISuggestion
from app.services.ticket_service import TicketService

# AI functions
from app.ai.classify import classify_ticket
from app.ai.embeddings import get_embedding
from app.ai.suggest import generate_suggested_reply

# Import our Redis event publisher
from app.core.events import publish_event

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

            # Retrieve the customer who created it to know their organization
            customer = await db.get(User, ticket.customer_id)
            if not customer:
                logger.error(f"Customer user #{ticket.customer_id} not found!")
                return

            # 2. Run the classification using the oMLX server wrapper
            # We pass the ticket's subject and body
            logger.info("Executing classificaion...")
            classification = classify_ticket(ticket.subject, ticket.body)
            ticket.priority = classification["priority"]
            ticket.category = classification["category"]
            ticket.sentiment = classification["sentiment"]

            # save classification results as an audit record in ai_suggestions
            classification_suggestion = AISuggestion(
                ticket_id=ticket.id,
                type="classification",
                content=classification,
                model=settings.LLM_MODEL
            )
            db.add(classification_suggestion)

            # Flush changes so database writes columns and generated ids
            await db.flush()

            # Broadcast real-time event that the ticket classification/triage is complete
            await publish_event(
                channel=f"org:{customer.org_id}",
                event_type="ticket.updated",
                data={
                    "ticket_id": ticket.id,
                    "category": ticket.category,
                    "priority": ticket.priority,
                    "sentiment": ticket.sentiment
                }
            )

            # 3. Generate Vector Embedding
            logger.info("Generating embedding...")
            combined_text = f"{ticket.subject}\n{ticket.body}"
            vector = get_embedding(combined_text)

            # save the vector in the database
            ticket_embedding = TicketEmbedding(
                ticket_id = ticket.id,
                embedding=vector
            )
            db.add(ticket_embedding)

            #Flush changes so the database knows the embedding exists
            # before we run similarity search
            await db.flush()

            # 4. Search for similar Resolved Tickets
            logger.info("Searching for similar resolved tickets...")
            similar_tickets = await TicketService.get_similar_resolved_tickets(
                db=db,
                user=customer, # Scopes search to the customer's organization
                ticket_id=ticket.id,
                limit=3
            )
            logger.info(f"Found {len(similar_tickets)} similar reolved tickets.")

            # 5. Generate RAG suggested reply
            logger.info("Generating suggested reply...")
            suggegsted_draft = generate_suggested_reply(ticket, similar_tickets)

            # Save the drafted reply in suggestions
            reply_suggestion = AISuggestion(
                ticket_id=ticket.id,
                type="reply",
                content={"reply": suggegsted_draft},
                model=settings.LLM_MODEL
            )
            db.add(reply_suggestion)
            await db.flush()

            # Broadcast real-time event that the AI reply suggestion is ready
            await publish_event(
                channel=f"org:{customer.org_id}",
                event_type="ai.suggestion.ready",
                data={
                    "ticket_id": ticket.id,
                    "suggestion_id": reply_suggestion.id
                }
            )

            # 6. Save and commit updates to Postgres
            await db.commit()
            logger.info(
                # f"Ticket #{ticket_id} successfully triaged by LLM. "
                # f"Category: {ticket.category}, Priority: {ticket.priority}, Sentiment: {ticket.sentiment}"
                f"Background processing successfully completed for ticket #{ticket.id}"
            )
    except Exception as e:
        logger.error(f"Error during background processing for ticket #{ticket_id}: {e}", exc_info=True)
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