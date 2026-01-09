"""
Centralized LLM Client Service
Abstracts LLM provider interactions, timeouts, and error handling.
Supports Vorpal (vLLM) and future backends.
"""

import httpx
import logging
from typing import List, Dict, Any, Optional, Union

from config import config

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified client for LLM interactions.
    Handles connection management, timeouts, and API format differences.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or config.VORPAL_URL
        self.model = model or config.VORPAL_MODEL
        self.timeout = config.REQUEST_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy load async client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client

    async def close(self):
        """Close the underlying client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def completion(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        logprobs: Optional[int] = None,
        echo: bool = False
    ) -> Dict[str, Any]:
        """
        Generate text completion (legacy/instruct mode).
        
        Returns:
            Dict containing 'text' and raw 'response' data.
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": stop,
            "logprobs": logprobs,
            "echo": echo
        }

        try:
            response = await client.post("/v1/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            text = data["choices"][0]["text"]
            return {"text": text.strip(), "raw": data}
            
        except httpx.HTTPError as e:
            logger.error(f"LLM Completion Error: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate chat completion.
        
        Returns:
            Dict containing 'content' (message content) and raw 'response' data.
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": stop
        }

        try:
            response = await client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            return {"content": content.strip(), "raw": data}
            
        except httpx.HTTPError as e:
            logger.error(f"LLM Chat Error: {e}")
            raise

    async def get_logprobs(self, text: str) -> Optional[float]:
        """
        Calculate perplexity/logprobs for text.
        Returns average log probability.
        """
        try:
            result = await self.completion(
                prompt=text,
                max_tokens=1,
                logprobs=1,
                echo=True,
                temperature=0.0
            )
            
            choices = result["raw"].get("choices", [])
            if not choices:
                return None
                
            token_logprobs = choices[0].get("logprobs", {}).get("token_logprobs", [])
            valid_logprobs = [lp for lp in token_logprobs if lp is not None]
            
            if not valid_logprobs:
                return None
                
            return sum(valid_logprobs) / len(valid_logprobs)
            
        except Exception as e:
            logger.warning(f"Failed to calculate logprobs: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if LLM service is reachable"""
        client = await self._get_client()
        try:
            response = await client.get("/health")
            return response.status_code == 200
        except Exception:
            return False

# Global instance
llm = LLMClient()
