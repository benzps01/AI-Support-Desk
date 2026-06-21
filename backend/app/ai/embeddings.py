import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

def get_embedding(text: str) -> list[float]:
    """
    Calls the local oMLX server to generate a 768-dimensional
    embedding vector for the given text.
    """
    # Clean the input text to remove unnecessary double spacing/newlines
    text = " ".join(text.split())

    base_url = settings.LLM_BASE_URL.rstrip('/')
    url = f"{base_url}/embeddings"

    payload = {
        "model": settings.EMBED_MODEL,
        "input": text
    }

    try:
        logger.info(f"Generating embedding from local server: {url}")

        # We establish a 10-second timeout for local embedding generation
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            embedding = result["data"][0]["embedding"]

            # Sanity check: Ensure we got the expected 768 dimensions for nomic
            if len(embedding) != 768:
                logger.warning(f"Expected 768 dimensions, but got {len(embedding)}!")

            return embedding
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        # Return a zero-vector fallback to prevent crashes if the embedding service is down
        # This keeps the ticket flow alive even if RAG is temporarily disabled
        return [0.0] * 768