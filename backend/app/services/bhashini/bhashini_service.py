"""
Bhashini (Digital India / NLTM - MeitY) Integration Service
Provides neural translation (NMT), Speech-to-Text (ASR), and Text-to-Speech (TTS)
for 11+ Indian languages with strict regulatory citation preservation (Rule 8.11).
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, Optional, Tuple, Any, List
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Supported Indian Language Codes mapped to Bhashini & Display Names
BHASHINI_LANGUAGES = {
    "en": {"name": "English", "native": "English", "bcp47": "en-IN"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "bcp47": "hi-IN"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "bcp47": "ta-IN"},
    "te": {"name": "Telugu", "native": "తెలుగు", "bcp47": "te-IN"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "bcp47": "kn-IN"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "bcp47": "ml-IN"},
    "mr": {"name": "Marathi", "native": "मराठी", "bcp47": "mr-IN"},
    "bn": {"name": "Bengali", "native": "বাংলা", "bcp47": "bn-IN"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "bcp47": "gu-IN"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "bcp47": "pa-IN"},
    "or": {"name": "Odia", "native": "ଓଡ଼ିଆ", "bcp47": "or-IN"}
}

def mask_legal_identifiers(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Mask legal citations (IS standards, clause references, and Gazette numbers)
    using invariant placeholder tokens to prevent alteration during translation (Rule 8.11).
    """
    tokens: Dict[str, str] = {}
    counter = 0

    def mask_token(match):
        nonlocal counter
        token = f"__LEGAL_ID_{counter}__"
        tokens[token] = match.group(0)
        counter += 1
        return token

    # Mask IS standards, e.g. IS 17526:2021, IS 4375, etc.
    masked = re.sub(r'\bIS\s+\d+(?:-\d+)*(?::\d{4})?\b', mask_token, text)
    # Mask clause references, e.g. Clause 4.2
    masked = re.sub(r'\b(?:Clause|cl\.)\s+\d+(?:\.\d+)*\b', mask_token, masked, flags=re.IGNORECASE)
    # Mask Gazette notification patterns
    masked = re.sub(r'\b(?:S\.O\.|G\.S\.R\.)\s*\d+\s*\([A-Z]\)\b', mask_token, masked)
    # Mask Scheme designations
    masked = re.sub(r'\bScheme\s+[IVXLCDM]+\b', mask_token, masked)
    return masked, tokens

def unmask_legal_identifiers(text: str, tokens: Dict[str, str]) -> str:
    """Restore original legal citations from placeholder tokens verbatim."""
    restored = text
    for token, orig in tokens.items():
        restored = restored.replace(token, orig)
    return restored


class BhashiniService:
    """
    Client for Digital India Bhashini ULCA / Dhruva inference pipelines.
    Supports NMT (Translation), ASR (Speech Recognition), and TTS (Voice Synthesis).
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = os.getenv("BHASHINI_API_KEY", self.settings.BHASHINI_API_KEY or "")
        self.user_id = os.getenv("BHASHINI_USER_ID", self.settings.BHASHINI_USER_ID or "")
        self.pipeline_id = os.getenv("BHASHINI_PIPELINE_ID", self.settings.BHASHINI_PIPELINE_ID or "64392f96daac500b55c543d7")
        self.inference_url = os.getenv("BHASHINI_INFERENCE_URL", self.settings.BHASHINI_INFERENCE_URL or "https://dhruva-api.bhashini.gov.in/services/inference/pipeline")
        self._cache: Dict[str, str] = {}
        self._timeout = 15.0

    def is_configured(self) -> bool:
        """Check whether valid Bhashini API credentials are set."""
        return bool(self.api_key.strip() and self.user_id.strip() and "your-" not in self.api_key)

    async def translate(self, text: str, source_lang: str = "en", target_lang: str = "hi") -> Optional[str]:
        """
        Translate text from source_lang to target_lang using Bhashini NMT.
        Preserves all legal tokens and standard numbers intact.
        Returns None if Bhashini is unconfigured or request fails, signaling fallback.
        """
        if not text or not text.strip():
            return text

        source = source_lang.lower().strip()
        target = target_lang.lower().strip()

        if source == target:
            return text

        cache_key = f"{source}:{target}:{hash(text.strip())}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.is_configured():
            return None

        # Mask technical citations
        masked_text, tokens = mask_legal_identifiers(text)

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "translation",
                    "config": {
                        "language": {
                            "sourceLanguage": source,
                            "targetLanguage": target
                        }
                    }
                }
            ],
            "inputData": {
                "input": [
                    {
                        "source": masked_text
                    }
                ]
            }
        }

        headers = {
            "Content-Type": "application/json",
            "ulcaApiKey": self.api_key,
            "userId": self.user_id
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self.inference_url,
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    pipeline_response = data.get("pipelineResponse", [])
                    if pipeline_response:
                        output_list = pipeline_response[0].get("output", [])
                        if output_list:
                            translated_masked = output_list[0].get("target", "")
                            if translated_masked:
                                final_translation = unmask_legal_identifiers(translated_masked, tokens)
                                self._cache[cache_key] = final_translation
                                return final_translation

                logger.warning(f"Bhashini translation API responded with status {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            logger.warning(f"Bhashini translation request failed: {e}. Falling back to resilient provider.")
            return None

    async def synthesize_speech(
        self,
        text: str,
        target_lang: str = "hi",
        gender: str = "female"
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesize speech audio from text using Bhashini Neural TTS.
        Returns dict with base64 audio and metadata, or None if unconfigured/failed.
        """
        if not text or not text.strip():
            return None

        target = target_lang.lower().strip()
        if not self.is_configured():
            return None

        # Clean text for speech synthesis
        clean_text = re.sub(r'[*#_`>]', '', text)
        clean_text = re.sub(r'\n+', '. ', clean_text).strip()
        # Truncate if extremely long to comply with TTS service limits
        if len(clean_text) > 900:
            clean_text = clean_text[:900] + "..."

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {
                            "sourceLanguage": target
                        },
                        "gender": gender
                    }
                }
            ],
            "inputData": {
                "input": [
                    {
                        "source": clean_text
                    }
                ]
            }
        }

        headers = {
            "Content-Type": "application/json",
            "ulcaApiKey": self.api_key,
            "userId": self.user_id
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self.inference_url,
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    pipeline_response = data.get("pipelineResponse", [])
                    if pipeline_response:
                        audio_list = pipeline_response[0].get("audio", [])
                        if audio_list and audio_list[0].get("audioContent"):
                            return {
                                "audio_content": audio_list[0]["audioContent"],
                                "audio_format": "wav",
                                "language": target,
                                "gender": gender,
                                "provider": "bhashini_nltm"
                            }

                logger.warning(f"Bhashini TTS API returned status {response.status_code}")
                return None

        except Exception as e:
            logger.warning(f"Bhashini TTS synthesis request failed: {e}")
            return None

    async def transcribe_speech(
        self,
        audio_base64: str,
        source_lang: str = "hi",
        audio_format: str = "wav"
    ) -> Optional[str]:
        """
        Transcribe spoken audio to text using Bhashini ASR.
        Returns recognized transcript string, or None if unconfigured/failed.
        """
        if not audio_base64 or not self.is_configured():
            return None

        source = source_lang.lower().strip()

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {
                            "sourceLanguage": source
                        },
                        "audioFormat": audio_format
                    }
                }
            ],
            "inputData": {
                "audio": [
                    {
                        "audioContent": audio_base64
                    }
                ]
            }
        }

        headers = {
            "Content-Type": "application/json",
            "ulcaApiKey": self.api_key,
            "userId": self.user_id
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self.inference_url,
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    pipeline_response = data.get("pipelineResponse", [])
                    if pipeline_response:
                        output_list = pipeline_response[0].get("output", [])
                        if output_list:
                            transcript = output_list[0].get("source", "")
                            return transcript.strip()

                logger.warning(f"Bhashini ASR API returned status {response.status_code}")
                return None

        except Exception as e:
            logger.warning(f"Bhashini ASR speech recognition failed: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current Bhashini integration diagnostic status."""
        configured = self.is_configured()
        return {
            "provider": "Digital India Bhashini (NLTM / MeitY)",
            "configured": configured,
            "inference_url": self.inference_url,
            "capabilities": ["nmt_translation", "asr_speech_recognition", "tts_voice_synthesis"],
            "supported_languages": list(BHASHINI_LANGUAGES.keys()),
            "language_details": BHASHINI_LANGUAGES,
            "fallback_enabled": True,
            "fallback_provider": "Resilient Dual LLM + Web Speech Synthesis",
            "active_mode": "bhashini_live" if configured else "bhashini_hybrid_fallback"
        }


# Singleton service instance
_bhashini_service: Optional[BhashiniService] = None

def get_bhashini_service() -> BhashiniService:
    global _bhashini_service
    if _bhashini_service is None:
        _bhashini_service = BhashiniService()
    return _bhashini_service
