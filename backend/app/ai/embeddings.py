import logging
from sentence_transformers import SentenceTransformer
from app.config import settings

logger = logging.getLogger(__name__)

# Global model instance. It will load once when the worker process boots up.
# We set trust_remote_code=True because nomic_embed-text requires custom modelling code from HF
# logger.info(f"Loading local SentenceTransformer model: {settings.EMBED_MODEL}")
# model = SentenceTransformer(settings.EMBED_MODEL, trust_remote_code=True)
_model = None

def get_embedding(text: str) -> list[float]:
    """
    Calls the local oMLX server to generate a 768-dimensional
    embedding vector for the given text.
    """

    global _model
    # Clean the input text to remove unnecessary double spacing/newlines
    text = " ".join(text.split())

    try:
        # Nomic text v1.5 expects search document inputs to be prefixed with 'search_document: '
        # this helps the model distinguish query vectors from document vectors
        prefix_text = f"search_document: {text}"

        # generate the embedding vector
        embedding = model.encode(prefix_text)

        #convert the numpy array to a standard python list of floats
        embedding_list = embedding.tolist()

        return embedding_list

    except Exception as e:
        logger.error(f"Failed to generate local embedding: {e}")
        # Return a zero-vector fallback in case of errors
        return [0.0] * 768