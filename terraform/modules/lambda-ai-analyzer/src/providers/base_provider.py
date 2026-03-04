"""
base_provider.py — Abstract base class for all AI provider implementations.

All AI providers must implement the `analyze` method which takes a prompt string
and returns a raw text response from the model.
"""

from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """Abstract base class defining the interface for AI providers."""

    def __init__(self, api_key: str, model: str):
        """
        Args:
            api_key: Provider-specific API key.
            model:   Model identifier string.
        """
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def analyze(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Send a prompt to the AI model and return the raw text response.

        Args:
            prompt:     The full prompt string to send.
            max_tokens: Maximum tokens in the response.

        Returns:
            Raw text response from the model (expected to be JSON).

        Raises:
            RuntimeError: If the API call fails or returns an error.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return self.__class__.__name__.replace("Provider", "").lower()
