"""
gemini_provider.py — Google Gemini AI provider with model fallback chain.

Free-tier model priority (all 0 usage by default):
  1. gemini-2.0-flash       (15 RPM, 1M TPM, 1.5B TPD)
  2. gemini-2.0-flash-lite  (30 RPM, lighter)
  3. gemini-1.5-flash        (15 RPM, 1M TPM, 50 requests/day free)

If a model returns HTTP 429 (RESOURCE_EXHAUSTED) or is unavailable, the
provider automatically falls back to the next model in the chain.
"""

import json
import urllib.request
import urllib.error
from .base_provider import BaseAIProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Fallback chain: primary → fallback → last-resort
FALLBACK_CHAIN = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]

# Max output tokens — JSON response only; 600 is sufficient for structured output
MAX_OUTPUT_TOKENS = 600


class GeminiProvider(BaseAIProvider):
    """Calls the Google Gemini generateContent REST endpoint with model fallback."""

    def analyze(self, prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS) -> str:
        """
        Send a prompt to Gemini, falling back through model chain on quota errors.

        Returns:
            Raw text from the model response.

        Raises:
            RuntimeError: If all models are exhausted.
        """
        # Build model chain: start with configured model, then fallback models
        models_to_try = _build_model_chain(self.model)
        last_error = None

        for model in models_to_try:
            try:
                return self._call_model(model, prompt, max_tokens)
            except RuntimeError as exc:
                err_str = str(exc)
                if _is_quota_error(err_str) or _is_not_found(err_str):
                    last_error = exc
                    continue  # try next model
                raise  # non-quota error — propagate immediately

        raise RuntimeError(
            f"All Gemini models exhausted. Last error: {last_error}"
        )

    def _call_model(self, model: str, prompt: str, max_tokens: int) -> str:
        """Call a specific Gemini model. Raises RuntimeError on any failure."""
        url = f"{GEMINI_API_BASE}/{model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.1,
                "topP": 0.8,
                "responseMimeType": "application/json",
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
            raise RuntimeError(f"Gemini[{model}] HTTP {exc.code}: {error_body[:300]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini[{model}] network error: {exc.reason}") from exc

        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Gemini[{model}] unexpected response: {str(body)[:200]}") from exc

        return text.strip()


def _build_model_chain(primary: str) -> list:
    """Return ordered list of models to try, starting with primary."""
    chain = [primary]
    for m in FALLBACK_CHAIN:
        if m != primary:
            chain.append(m)
    return chain


def _is_quota_error(err_str: str) -> bool:
    """Return True if error is a rate-limit/quota error."""
    quota_signals = ["429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "rateLimitExceeded"]
    lower = err_str.lower()
    return any(s.lower() in lower for s in quota_signals)


def _is_not_found(err_str: str) -> bool:
    """Return True if model does not exist (404)."""
    return "404" in err_str or "not found" in err_str.lower()
