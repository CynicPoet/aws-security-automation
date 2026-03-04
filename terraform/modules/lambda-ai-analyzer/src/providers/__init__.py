# AI provider package — exposes factory function
from .gemini_provider import GeminiProvider
from .claude_provider import ClaudeProvider


def get_provider(provider_name: str, api_key: str, model: str):
    """
    Factory — return the correct AI provider instance.

    Args:
        provider_name: 'gemini' or 'claude'
        api_key:       API key for the chosen provider
        model:         Model name (e.g. 'gemini-2.5-flash', 'claude-3-5-sonnet-20241022')
    """
    if provider_name.lower() == "gemini":
        return GeminiProvider(api_key=api_key, model=model)
    elif provider_name.lower() == "claude":
        return ClaudeProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unknown AI provider: {provider_name!r}. Supported: 'gemini', 'claude'")
