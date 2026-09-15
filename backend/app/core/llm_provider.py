from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send a chat completion request"""
        pass

    @abstractmethod
    async def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: BaseModel,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> BaseModel:
        """Get structured output matching a Pydantic model"""
        pass

class LLMResponse(BaseModel):
    """Standardized LLM response"""
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: str
    finish_reason: Optional[str] = None

class StructuredLLMResponse(BaseModel):
    """Structured LLM response with parsed data"""
    data: BaseModel
    raw_content: str
    usage: Optional[Dict[str, Any]] = None
    model: str
    finish_reason: Optional[str] = None