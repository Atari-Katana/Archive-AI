import httpx
import logging
from fastapi import HTTPException
from typing import List, Dict

from config import config
from stream_handler import stream_handler
from services.persona_manager import personas_manager
from schemas.chat import ChatResponse

logger = logging.getLogger("brain.chat")

class ChatService:
    async def process_chat(self, message: str) -> ChatResponse:
        # Capture input to Redis Stream (non-blocking, fire and forget)
        await stream_handler.capture_input(message)

        # Get active persona prompt
        active_persona = personas_manager.get_active_persona()
        messages = []

        if active_persona:
            system_content = active_persona.personality
            if active_persona.history:
                system_content += f"\n\nContext/History: {active_persona.history}"
            messages.append({"role": "system", "content": system_content})

        messages.append({"role": "user", "content": message})

        # 1. Try Primary Engine: Bolt-XL
        logger.info(f"Attempting primary engine: Bolt-XL ({config.BOLT_XL_URL})")
        try:
            return await self._call_engine(
                config.BOLT_XL_URL,
                config.BOLT_XL_MODEL,
                messages,
                "bolt-xl"
            )
        except Exception as e:
            logger.warning(f"Bolt-XL failed: {str(e)}. Falling back to Vorpal.")

        # 2. Fallback Engine: Vorpal
        logger.info(f"Attempting fallback engine: Vorpal ({config.VORPAL_URL})")
        try:
            return await self._call_engine(
                config.VORPAL_URL,
                config.VORPAL_MODEL,
                messages,
                "vorpal"
            )
        except Exception as e:
            logger.error(f"Vorpal failed: {str(e)}.")
            raise HTTPException(
                status_code=503,
                detail=f"All engines failed. Last error: {str(e)}"
            )

    async def _call_engine(self, base_url: str, model: str, messages: List[Dict[str, str]], engine_name: str) -> ChatResponse:
        """Helper to call an OpenAI-compatible completion endpoint"""
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": config.MAX_TOKENS,
                "temperature": 0.1,
                "top_p": 0.9
            }

            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            completion_text = result['choices'][0]['message']['content']

            return ChatResponse(
                response=completion_text,
                engine=engine_name
            )

chat_service = ChatService()
