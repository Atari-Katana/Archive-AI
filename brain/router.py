"""
Semantic Router (Chunk 2.6)
Routes user queries to appropriate handlers based on intent classification.
Uses keyword matching for basic intent detection.
"""

import re
from typing import Dict, Any, Optional
from enum import Enum


class Intent(str, Enum):
    """Supported intents"""
    CHAT = "chat"
    SEARCH_MEMORY = "search_memory"
    HELP = "help"


class SemanticRouter:
    """Routes user queries based on intent classification"""

    # Intent patterns (keyword-based)
    PATTERNS = {
        Intent.SEARCH_MEMORY: [
            r"\b(remember|recall|search|find|lookup|what did i say)\b",
            r"\b(previous|earlier|before|past)\b.*\b(conversation|message|topic)\b",
            r"\b(history|memories)\b",
        ],
        Intent.HELP: [
            r"\b(help|assist|guide|how do|what can|commands)\b",
            r"\b(instructions|tutorial|explain)\b.*\b(works?|use)\b",
            r"^\s*(help|\?|what)\s*$",
        ],
    }

    def route(self, message: str) -> Dict[str, Any]:
        """
        Route a message to the appropriate intent.

        Args:
            message: User message to route

        Returns:
            Dict with:
                - intent: Intent enum value
                - confidence: Confidence score (0.0-1.0)
                - params: Extracted parameters (varies by intent)
        """
        if not message or not message.strip():
            return {
                "intent": Intent.CHAT,
                "confidence": 1.0,
                "params": {}
            }

        message_lower = message.lower().strip()

        # Check each intent pattern
        for intent, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    params = self._extract_params(intent, message_lower)
                    return {
                        "intent": intent,
                        "confidence": 0.9,  # High confidence for keyword match
                        "params": params
                    }

        # Default to chat if no pattern matches
        return {
            "intent": Intent.CHAT,
            "confidence": 0.8,
            "params": {}
        }

    def _extract_params(self, intent: Intent, message: str) -> Dict[str, Any]:
        """
        Extract intent-specific parameters from message.

        Args:
            intent: Detected intent
            message: Lowercased message

        Returns:
            Dict of extracted parameters
        """
        params = {}

        if intent == Intent.SEARCH_MEMORY:
            # Extract search query
            # Remove trigger words to get the actual query
            query = message
            for word in ["remember", "recall", "search", "find", "lookup",
                         "what did i say about", "what did i say"]:
                query = query.replace(word, "").strip()

            # Remove common filler words
            query = re.sub(r"\b(the|a|an|about|for|to)\b", "", query).strip()

            params["query"] = query if query else message

        return params


# Global instance
router = SemanticRouter()
