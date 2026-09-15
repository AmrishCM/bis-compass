import httpx
import json
import logging
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel

from app.core.llm_provider import LLMProvider, LLMResponse, StructuredLLMResponse

logger = logging.getLogger(__name__)

class NVIDIAProvider(LLMProvider):
    """NVIDIA NIM API provider implementation"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        chat_model: str = "openai/gpt-oss-120b",
        embed_model: str = "nvidia/nemotron-3-embed-1b",
        fallback_chat_model: Optional[str] = None
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.fallback_chat_model = fallback_chat_model
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key != "your_nvidia_api_key_here":
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=headers
        )
        self.call_stats = {
            "llm_provider": "NVIDIA",
            "llm_model": self.chat_model,
            "llm_called": False,
            "llm_calls_count": 0,
            "llm_latency": 0.0,
            "llm_error": None,
            "embedding_model": self.embed_model
        }

    def get_execution_telemetry(self) -> Dict[str, Any]:
        """Return runtime LLM execution audit telemetry (Section 18)"""
        return dict(self.call_stats)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request to NVIDIA NIM API"""
        if not self.api_key or self.api_key == "your_nvidia_api_key_here":
            self.call_stats["llm_error"] = "NVIDIA_API_KEY is not configured"
            raise ValueError("NVIDIA_API_KEY is not configured. Running in local fallback mode.")

        import time
        t0 = time.time()
        self.call_stats["llm_called"] = True
        self.call_stats["llm_calls_count"] += 1

        try:
            payload = {
                "model": self.chat_model,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }

            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            # Add any additional parameters
            payload.update(kwargs)

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            latency = time.time() - t0
            self.call_stats["llm_latency"] += latency
            self.call_stats["llm_model"] = result.get("model", self.chat_model)

            return LLMResponse(
                content=result["choices"][0]["message"]["content"],
                usage=result.get("usage"),
                model=result.get("model", self.chat_model),
                finish_reason=result["choices"][0].get("finish_reason")
            )

        except Exception as e:
            logger.error(f"NVIDIA API chat error: {str(e)}")
            # Try fallback model if available
            if self.fallback_chat_model:
                logger.info(f"Trying fallback model: {self.fallback_chat_model}")
                try:
                    payload["model"] = self.fallback_chat_model
                    response = await self.client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload
                    )
                    response.raise_for_status()

                    result = response.json()
                    latency = time.time() - t0
                    self.call_stats["llm_latency"] += latency
                    self.call_stats["llm_model"] = result.get("model", self.fallback_chat_model)

                    return LLMResponse(
                        content=result["choices"][0]["message"]["content"],
                        usage=result.get("usage"),
                        model=result.get("model", self.fallback_chat_model),
                        finish_reason=result["choices"][0].get("finish_reason")
                    )
                except Exception as fallback_error:
                    self.call_stats["llm_error"] = str(fallback_error)
                    logger.error(f"Fallback model also failed: {str(fallback_error)}")
                    raise fallback_error
            else:
                self.call_stats["llm_error"] = str(e)
                raise e

    async def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> StructuredLLMResponse:
        """Get structured output matching a Pydantic model"""
        if not self.api_key or self.api_key == "your_nvidia_api_key_here":
            raise ValueError("NVIDIA_API_KEY is not configured. Running in local fallback mode.")
        try:
            # Add instruction for JSON output
            json_instruction = {
                "role": "system",
                "content": "You must respond with valid JSON that matches the requested schema exactly. Do not include any additional text or explanation."
            }

            # Insert JSON instruction at the beginning of messages
            structured_messages = [json_instruction] + messages

            payload = {
                "model": self.chat_model,
                "messages": structured_messages,
                "temperature": temperature,
                "stream": False
            }

            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            # Add any additional parameters
            payload.update(kwargs)

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            raw_content = result["choices"][0]["message"]["content"]

            # Try to parse JSON from the response
            try:
                # Extract JSON from response (handle potential markdown formatting)
                content = raw_content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                parsed_data = json.loads(content)
                validated_data = response_model(**parsed_data)

            except (json.JSONDecodeError, Exception) as parse_error:
                logger.warning(f"Failed to parse JSON from LLM response: {parse_error}")
                logger.warning(f"Raw content: {raw_content}")
                # Fallback: try to extract JSON using more aggressive parsing
                import re
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    try:
                        parsed_data = json.loads(json_match.group())
                        validated_data = response_model(**parsed_data)
                    except Exception as e2:
                        logger.error(f"Secondary JSON parsing failed: {e2}")
                        raise ValueError(f"Could not parse valid JSON from LLM response: {raw_content}")
                else:
                    raise ValueError(f"No JSON found in LLM response: {raw_content}")

            return StructuredLLMResponse(
                data=validated_data,
                raw_content=raw_content,
                usage=result.get("usage"),
                model=result.get("model", self.chat_model),
                finish_reason=result["choices"][0].get("finish_reason")
            )

        except Exception as e:
            logger.error(f"NVIDIA API structured output error: {str(e)}")
            # Try fallback model if available
            if self.fallback_chat_model:
                logger.info(f"Trying fallback model for structured output: {self.fallback_chat_model}")
                try:
                    payload["model"] = self.fallback_chat_model
                    response = await self.client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload
                    )
                    response.raise_for_status()

                    result = response.json()
                    raw_content = result["choices"][0]["message"]["content"]

                    # Parse JSON from fallback response
                    content = raw_content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

                    parsed_data = json.loads(content)
                    validated_data = response_model(**parsed_data)

                    return StructuredLLMResponse(
                        data=validated_data,
                        raw_content=raw_content,
                        usage=result.get("usage"),
                        model=result.get("model", self.fallback_chat_model),
                        finish_reason=result["choices"][0].get("finish_reason")
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed for structured output: {str(fallback_error)}")
                    raise fallback_error
            else:
                raise e

    async def health_check(self) -> Dict[str, Any]:
        """Perform minimal authenticated test completion measuring real roundtrip latency"""
        import time
        if not self.api_key or self.api_key == "your_nvidia_api_key_here":
            return {
                "provider": "nvidia",
                "configured": False,
                "reachable": False,
                "model": self.chat_model,
                "latency_ms": None,
                "error": "NVIDIA_API_KEY is not configured"
            }

        t0 = time.time()
        try:
            payload = {
                "model": self.chat_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
                "temperature": 0.1
            }
            resp = await self.client.post(f"{self.base_url}/chat/completions", json=payload, timeout=8.0)
            latency_ms = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                return {
                    "provider": "nvidia",
                    "configured": True,
                    "reachable": True,
                    "model": self.chat_model,
                    "latency_ms": latency_ms,
                    "error": None
                }
            else:
                return {
                    "provider": "nvidia",
                    "configured": True,
                    "reachable": False,
                    "model": self.chat_model,
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}: {resp.text[:120]}"
                }
        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            return {
                "provider": "nvidia",
                "configured": True,
                "reachable": False,
                "model": self.chat_model,
                "latency_ms": latency_ms,
                "error": str(e)
            }

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()