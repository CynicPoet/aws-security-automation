"""
claude_provider.py — Anthropic Claude AI provider using REST API via urllib.

No external dependencies — uses Python stdlib urllib.request only.
Swap to this provider by setting ai_provider='claude' and updating
the API key in Secrets Manager.

API reference: https://docs.anthropic.com/claude/reference/messages_post
"""

import json
import urllib.request
import urllib.error
from .base_provider import BaseAIProvider

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeProvider(BaseAIProvider):
    """Calls the Anthropic Claude Messages REST endpoint."""

    def analyze(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Send a prompt to Claude and return the raw text response.

        Args:
            prompt:     Full prompt to send.
            max_tokens: Maximum output tokens.

        Returns:
            Raw text from the model response.

        Raises:
            RuntimeError: On HTTP error or unexpected response shape.
        """
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            CLAUDE_API_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise RuntimeError(f"Claude API HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Claude API network error: {exc.reason}") from exc

        # Extract text from content[0].text
        try:
            text = body["content"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected Claude response structure: {body}") from exc

        return text.strip()
