import abc
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient(abc.ABC):
    """
    Abstract Base Class for LLM Providers.
    Establishes the contract that all providers must implement.
    """

    @abc.abstractmethod
    def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a chat completion from a prompt"""
        pass
    
class LocalLLMClient(LLMClient):
    """
    Client for OpenAI-compatible local model servers
    """
    def __init__(self):
        #Base URL from config
        self.base_url = settings.LLM_BASE_URL.rstrip('/')
        self.model = settings.LLM_MODEL

        #We establish a client timeout of 30 seconds for local inference calls
        self.client = httpx.Client(timeout=30.0)
        logger.info(f"Initialized LocalLLMClient with base URL: {self.base_url}, model: {self.model}")

    def complete(self, prompt: str, system_prompt: str = "") -> str:
        url = f"{self.base_url}/chat/completions"

        #Assemble standard openAI chat message payloads
        messages = []
        if system_prompt:
            messages.append({"role":"system", "content": system_prompt})
        messages.append({"role":"user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0, #0.0 means deterministic outputs
            "stream": False
        }

        try:
            logger.info(f"Sending chat completion request to local server: {url}")
            response = self.client.post(url, json=payload)
            response.raise_for_status()

            #Extract standard OpenAI chat completion response format
            result = response.json()
            completed_text = result["choices"][0]["message"]["content"]
            return completed_text.strip()
        
        except Exception as e:
            logger.error(f"Error calling local LLM Server: {e}")
            raise RuntimeError(f"LLM call failed: {e}") from e

def get_llm_client() -> LLMClient:
    """
    Factory function to retrieve the configured LLM CLient.
    Easily expandable to return hosted clients (OpenAI/Anthropic) based on config
    """
    if settings.LLM_PROVIDER == "local":
        return LocalLLMClient()
    else:
        # Placeholder for other providers
        raise ValueError(f"Unsupported LLM Provider: {settings.LLM_PROVIDER}")