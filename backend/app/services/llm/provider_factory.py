import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Type
from dotenv import load_dotenv
import logging
from pydantic import BaseModel

from app.core.llm_provider import LLMProvider, LLMResponse, StructuredLLMResponse
from app.services.llm.nvidia_provider import NVIDIAProvider
from app.services.llm.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

def _ensure_env_loaded():
    load_dotenv()
    if not os.getenv("NVIDIA_API_KEY") or not os.getenv("GROQ_API_KEY"):
        backend_env = Path(__file__).resolve().parents[3] / ".env"
        if backend_env.exists():
            load_dotenv(backend_env, override=False)

class ResilientDualLLMProvider(LLMProvider):
    """
    Seamless Dual-LLM Failover Provider.
    Tries primary LLM provider first; automatically fails over to secondary LLM
    provider if the primary experiences rate-limits, model errors, or network timeouts.
    """

    def __init__(self, primary: LLMProvider, secondary: LLMProvider):
        self.primary = primary
        self.secondary = secondary

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        try:
            return await self.primary.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        except Exception as primary_err:
            logger.warning(
                f"Primary LLM ({getattr(self.primary, 'chat_model', 'primary')}) failed: {primary_err}. "
                f"Failing over to secondary LLM ({getattr(self.secondary, 'chat_model', 'secondary')})."
            )
            return await self.secondary.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

    async def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> StructuredLLMResponse:
        try:
            return await self.primary.structured_output(
                messages=messages,
                response_model=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        except Exception as primary_err:
            logger.warning(
                f"Primary LLM structured output failed: {primary_err}. "
                f"Failing over to secondary LLM ({getattr(self.secondary, 'chat_model', 'secondary')})."
            )
            return await self.secondary.structured_output(
                messages=messages,
                response_model=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings (delegates to NVIDIA provider if available)"""
        if hasattr(self.primary, "embed"):
            return await self.primary.embed(texts)
        if hasattr(self.secondary, "embed"):
            return await self.secondary.embed(texts)
        raise NotImplementedError("Neither LLM provider supports embedding generation.")

    def get_execution_telemetry(self) -> Dict[str, Any]:
        p_tel = self.primary.get_execution_telemetry() if hasattr(self.primary, "get_execution_telemetry") else {}
        s_tel = self.secondary.get_execution_telemetry() if hasattr(self.secondary, "get_execution_telemetry") else {}
        return {
            "primary": p_tel,
            "secondary": s_tel
        }

class LLMProviderFactory:
    """Factory for creating LLM providers with automatic environment variable fallback"""

    @staticmethod
    def create_provider(
        provider_type: str = "dual",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        fallback_chat_model: Optional[str] = None
    ) -> LLMProvider:
        """Create an LLM provider instance with robust defaults from .env"""
        _ensure_env_loaded()

        p_type = provider_type.lower()
        if p_type == "nvidia":
            return NVIDIAProvider(
                api_key=api_key or os.getenv("NVIDIA_API_KEY", ""),
                base_url=base_url or os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                chat_model=chat_model or os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.2-11b-vision-instruct"),
                embed_model=embed_model or os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b"),
                fallback_chat_model=fallback_chat_model or os.getenv("NVIDIA_FALLBACK_CHAT_MODEL", "mistralai/mistral-nemotron")
            )
        elif p_type == "groq":
            return GroqProvider(
                api_key=api_key or os.getenv("GROQ_API_KEY", ""),
                base_url=base_url or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                chat_model=chat_model or os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b"),
                fallback_chat_model=fallback_chat_model or os.getenv("GROQ_FALLBACK_CHAT_MODEL", "openai/gpt-oss-20b")
            )
        elif p_type in ["dual", "failover", "resilient"]:
            nvidia = LLMProviderFactory.create_provider(provider_type="nvidia")
            groq = LLMProviderFactory.create_provider(provider_type="groq")
            return ResilientDualLLMProvider(primary=nvidia, secondary=groq)
        else:
            raise ValueError(f"Unsupported LLM provider type: {provider_type}")

# Global provider instance
_llm_provider: Optional[LLMProvider] = None

def get_llm_provider() -> LLMProvider:
    """Get the global LLM provider instance (defaults to ResilientDualLLMProvider)"""
    global _llm_provider
    if _llm_provider is None:
        _ensure_env_loaded()
        _llm_provider = LLMProviderFactory.create_provider("dual")
        logger.info("Initialized Resilient Dual LLM provider (NVIDIA + Groq)")
    return _llm_provider

def set_llm_provider(provider: LLMProvider):
    """Set the global LLM provider instance (useful for testing)"""
    global _llm_provider
    _llm_provider = provider