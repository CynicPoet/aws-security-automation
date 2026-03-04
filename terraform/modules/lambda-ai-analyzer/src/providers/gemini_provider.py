"""
gemini_provider.py — Google Gemini AI provider using REST API via urllib.

No external dependencies — uses Python stdlib urllib.request only.
Compatible with Gemini free tier: gemini-2.5-flash (10 RPM, 250 RPD).

API reference: https://ai.google.dev/api/rest/v1beta/models/generateContent
"""

import json
import urllib.request
import urllib.error
from .base_provider import BaseAIProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(BaseAIProvider):
    """Calls the Google Gemini generateContent REST endpoint."""

    def analyze(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Send a prompt to Gemini and return the raw text response.

        Args:
            prompt:     Full prompt to send.
            max_tokens: Maximum output tokens (Gemini uses maxOutputTokens).

        Returns:
            Raw text from the model response.

        Raises:
            RuntimeError: On HTTP error or unexpected response shape.
        """
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.1,       # Low temperature for deterministic JSON output
                "topP": 0.8,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise RuntimeError(f"Gemini API HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini API network error: {exc.reason}") from exc

        # Extract text from candidates[0].content.parts[0].text
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected Gemini response structure: {body}") from exc

        return text.strip()
