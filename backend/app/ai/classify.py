from sqlalchemy.sql.operators import endswith_op
import json
import logging
from typing import Literal
from pydantic import BaseModel, Field

from app.ai.client import get_llm_client
from app.ai.prompts import CLASSIFICAION_SYSTEM_PROMPT, CLASSIFICATION_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# 1. Define the pydantic schema for validation
class TicketClassification(BaseModel):
    category: str = Field(default="general")
    priority: Literal["low", "medium", "high", "urgent"] = Field(default="medium")
    sentiment: Literal["positive", "neutral", "negative"] = Field(default="neutral")

def clean_llm_json(text: str) -> str:
    """
    Strips markdown formatting block wraps (```json ... ```)
    that LLMs frequently output.
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def classify_ticket(subject: str, body: str) -> dict:
    """
    Sends the ticket to the LLM for classification,
    parses the JSON response, and validates it.
    """

    # Create the user prompt with the actual ticket contents
    user_prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(subject=subject, body=body)

    # Defaults in case of failures (Graceful degradation)
    fallback_data = {
        "category": "general",
        "priority": "medium",
        "sentiment": "neutral"
    }

    try:
        # Get the LLM client
        llm = get_llm_client()

        # Call the model
        raw_response = llm.complete(
            prompt=user_prompt,
            system_prompt=CLASSIFICAION_SYSTEM_PROMPT
        )

        ## Clean and parse JSON
        cleaned_json = clean_llm_json(raw_response)
        parsed_dict = json.loads(cleaned_json)

        # validate schema constraints using pydantic
        validated_data = TicketClassification(**parsed_dict)

        logger.info(f"Successfully classified ticket. Results: {validated_data.model_dump()}")
        return validated_data.model_dump()

    except json.JSONDecodeError as jde:
        logger.error(f"LLM returned invalid JSON. Raw response: '{raw_response}', Error: {jde}")
        return fallback_data
    except Exception as e:
        logger.error(f"Error during ticket classification: {e}")
        return fallback_data