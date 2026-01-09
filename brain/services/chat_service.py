import httpx
import logging
from fastapi import HTTPException

from config import config
from stream_handler import stream_handler
from services.persona_manager import personas_manager
from schemas.chat import ChatResponse

logger = logging.getLogger("brain.chat")

class ChatService:
    async def process_chat(self, message: str) -> ChatResponse:
        # Capture input to Redis Stream (non-blocking, fire and forget)
        await stream_handler.capture_input(message)

        # Route through Bifrost gateway
        # Bifrost handles semantic routing to determine the appropriate model
        # Default to vorpal, but Bifrost may override based on query complexity
        bifrost_model = f"vorpal/{config.VORPAL_MODEL}"

        logger.info(f"Routing message to Bifrost (Model: {bifrost_model})")

        # Get active persona prompt
        active_persona = personas_manager.get_active_persona()
        messages = []
        
        if active_persona:
            system_content = active_persona.personality
            if active_persona.history:
                system_content += f"\n\nContext/History: {active_persona.history}"
            messages.append({"role": "system", "content": system_content})
        
        messages.append({"role": "user", "content": message})

        try:
            # Proxy request to Bifrost (OpenAI-compatible API)
            async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                bifrost_payload = {
                    "model": bifrost_model,
                    "messages": messages,
                    "max_tokens": config.MAX_TOKENS,
                    "temperature": 0.7
                }

                response = await client.post(
                    f"{config.BIFROST_URL}/v1/chat/completions",
                    json=bifrost_payload
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract response text and model info
                completion_text = result['choices'][0]['message']['content']
                used_model = result.get('model', bifrost_model)

                return ChatResponse(
                    response=completion_text,
                    engine=f"bifrost:{used_model}"
                )

        except httpx.HTTPError as e:
            # Fallback to direct Vorpal if Bifrost fails
            logger.warning(f"Bifrost error: {str(e)}. Falling back to direct Vorpal.")
            try:
                async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                    vorpal_payload = {
                        "model": config.VORPAL_MODEL,
                        "messages": messages,
                        "max_tokens": config.MAX_TOKENS,
                        "temperature": 0.7
                    }
                    response = await client.post(
                        f"{config.VORPAL_URL}/v1/chat/completions",
                        json=vorpal_payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    return ChatResponse(
                        response=result['choices'][0]['message']['content'],
                        engine="vorpal-fallback"
                    )
            except Exception as ve:
                raise HTTPException(
                    status_code=503,
                    detail=f"Both Bifrost and Vorpal fallback failed: {str(ve)}"
                )

chat_service = ChatService()
