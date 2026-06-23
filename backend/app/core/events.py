import json
import logging
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

# initialize a peersistent async Redis Client.
# Decode response = True automatically converts binary Redis bytes into string text.
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def publish_event(channel: str, event_type: str, data: dict):
    """
    Serializes data into JSON and publishes it to a Redis channel.
    FastAPI and celery can both call this function to broadcast events.
    """
    try:
        payload = {
            "event": event_type,
            "data": data
        }

        message = json.dumps(payload)
        logger.info(f"Publishing event '{event_type}' to Redis channel: '{channel}'")

        # Publish the raw JSON string to the channel
        await redis_client.publish(channel, message)
    
    except Exception as e:
        logger.error(f"Failed to publish event to Redis: {e}")