import logging
from app.models.ticket import Ticket
from app.ai.client import get_llm_client
from app.ai.prompts import SUGGEST_REPLY_SYSTEM_PROMPT, SUGGEST_REPLY_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

def generate_suggested_reply(ticket: Ticket, similar_tickets: list[Ticket]) -> str:
    """
    Assembles similar resolved tickets as context, formats the RAG prompt,
    and asks the LLM to draft a response.
    """
    context_blocks = []

    # 1. Loop through past resolved tickets and extract the resolution message
    for idx, sim in enumerate(similar_tickets, 1):
        # we find the last public message sent on the ticket
        # (which is usually the resolving answer)
        public_messages = [m for m in sim.messages if not m.is_internal_note]
        resolution_body = public_messages[-1].body if public_messages else "No message thread available."

        block = (
            f"PAST TICKET #{idx}:\n"
            f"Subject: {sim.subject}\n"
            f"Description: {sim.body}\n"
            f"Resolution: {resolution_body}\n"
            f"----------------------------------------" 
        )
        context_blocks.append(block)

    # combine all similar tickets into a single context string
    context_str = "\n\n".join(context_blocks) if context_blocks else "No similar past tickets found."

    # 2. Compile the user prompt
    user_prompt = SUGGEST_REPLY_USER_PROMPT_TEMPLATE.format(
        context=context_str,
        subject=ticket.subject,
        body=ticket.body
    )

    try:
        # Get the LLM client
        llm = get_llm_client()

        # 3. Call the model
        logger.info(f"Generating suggested reply for ticket #{ticket.id} using RAG.")
        suggested_draft = llm.complete(
            prompt=user_prompt,
            system_prompt=SUGGEST_REPLY_SYSTEM_PROMPT
        )

        return suggested_draft.strip()

    except Exception as e:
        logger.error(f"Error generating suggested reply: {e}")
        # Default placeholder reply in case of failure
        return "Thank you for contacting support. We have received your ticket and will look into it shortly."