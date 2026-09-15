from typing import Optional
from app.core.llm_provider import LLMProvider
from app.services.llm.nvidia_provider import NVIDIAProvider
import logging

logger = logging.getLogger(__name__)

class LLMProviderFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create_provider(
        provider_type: str = "nvidia",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        fallback_chat_model: Optional[str] = None
    ) -> LLMProvider:
        """Create an LLM provider instance"""

        if provider_type.lower() == "nvidia":
            return NVIDIAProvider(
                api_key=api_key or "",
                base_url=base_url or "https://integrate.api.nvidia.com/v1",
                chat_model=chat_model or "openai/gpt-oss-120b",
                embed_model=embed_model or "nvidia/nemotron-3-embed-1b",
                fallback_chat_model=fallback_chat_model
            )
        else:
            raise ValueError(f"Unsupported LLM provider type: {provider_type}")

# Global provider instance
_llm_provider: Optional[LLMProvider] = None

def get_llm_provider() -> LLMProvider:
    """Get the global LLM provider instance"""
    global _llm_provider
    if _llm_provider is None:
        # In a real application, these would come from environment variables/config
        import os
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv()
        if not os.getenv("NVIDIA_API_KEY"):
            backend_env = Path(__file__).resolve().parents[3] / ".env"
            if backend_env.exists():
                load_dotenv(backend_env)

        _llm_provider = LLMProviderFactory.create_provider(
            api_key=os.getenv("NVIDIA_API_KEY"),
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            chat_model=os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.2-11b-vision-instruct"),
            embed_model=os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b"),
            fallback_chat_model=os.getenv("NVIDIA_FALLBACK_CHAT_MODEL", "mistralai/mistral-nemotron")
        )
        logger.info("Initialized LLM provider")
    return _llm_provider

def set_llm_provider(provider: LLMProvider):
    """Set the global LLM provider instance (useful for testing)"""
    global _llm_provider
    _llm_provider = provider