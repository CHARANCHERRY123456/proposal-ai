"""
Gemini API client — single place to configure Gemini for ask/response.

Usage:
    from clients import GeminiClient

    gemini = GeminiClient()
    answer = gemini.ask("What is RAG?")
"""

import os
from typing import Optional

from dotenv import load_dotenv
from google import genai

load_dotenv()


DEFAULT_MODEL = "models/gemma-3-12b-it"


class GeminiClient:
    """Gemini client for asking questions and getting responses."""

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Set GEMINI_API_KEY in .env or pass api_key=..."
            )
        self._client = genai.Client(api_key=api_key)

    def ask(
        self,
        question: str,
        *,
        model: str = DEFAULT_MODEL,
        **kwargs,
    ) -> str:
        """Ask a question and get the response text."""
        response = self._client.models.generate_content(
            model=model,
            contents=question,
            **kwargs,
        )
        return response.text
