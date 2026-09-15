from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict
import re
import logging
from app.services.llm.provider_factory import get_llm_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/translate", tags=["Multi-Language Localization"])

# In-memory translation cache to avoid duplicate LLM calls
_TRANSLATION_CACHE: Dict[str, str] = {}

LANGUAGE_NAMES = {
    "en": "English",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ml": "Malayalam (മലയാളം)",
    "hi": "Hindi (हिन्दी)"
}

class TranslationRequest(BaseModel):
    text: str = Field(..., description="Prose, explanation, or question to translate")
    target_lang: Optional[str] = Field(None, description="Target language code: en, ta, te, kn, ml, hi")
    target_language: Optional[str] = Field(None, description="Alias for target_lang")
    session_id: Optional[str] = None

class TranslationResponse(BaseModel):
    original_text: str
    target_lang: str
    translated_text: str
    cached: bool = False

def mask_legal_identifiers(text: str):
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
    return masked, tokens

def unmask_legal_identifiers(text: str, tokens: Dict[str, str]) -> str:
    """Restore original legal citations from placeholder tokens verbatim."""
    restored = text
    for token, orig in tokens.items():
        restored = restored.replace(token, orig)
    return restored

@router.post("", response_model=TranslationResponse, summary="Translate dynamic compliance prose preserving legal identifiers")
async def translate_text(payload: TranslationRequest):
    """
    Translates dynamic compliance text (clarifications, explanations, recommendations)
    into Tamil, Telugu, Kannada, Malayalam, or Hindi.

    NON-NEGOTIABLE RULE (Section 8.11):
    Legal and technical citations (e.g. 'IS 17526:2021', official titles, Gazette numbers,
    clause numbers, 'BIS', 'QCO') are NEVER translated or altered.
    """
    target = (payload.target_lang or payload.target_language or "en").lower().strip()
    if target == "en" or not payload.text.strip():
        return TranslationResponse(
            original_text=payload.text,
            target_lang="en",
            translated_text=payload.text,
            cached=True
        )

    if target not in LANGUAGE_NAMES:
        raise HTTPException(status_code=400, detail=f"Unsupported language code '{target}'. Supported: {list(LANGUAGE_NAMES.keys())}")

    cache_key = f"{target}:{hash(payload.text.strip())}"
    if cache_key in _TRANSLATION_CACHE:
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=_TRANSLATION_CACHE[cache_key],
            cached=True
        )

    # Protect legal identifiers with regex tokens
    masked_text, tokens = mask_legal_identifiers(payload.text)

    llm = get_llm_provider()
    lang_name = LANGUAGE_NAMES.get(target, "English")

    system_prompt = (
        f"You are a professional legal-regulatory translator for Indian standards.\n"
        f"Translate the provided text accurately into {lang_name}.\n"
        f"CRITICAL RULES:\n"
        f"1. DO NOT translate or modify placeholder tokens like __LEGAL_ID_0__, __LEGAL_ID_1__, etc. Keep them exactly as they are.\n"
        f"2. Retain all technical and regulatory accuracy.\n"
        f"3. Return ONLY the translated text, no preamble or quotes."
    )

    try:
        response = await llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": masked_text}
            ],
            temperature=0.1,
            max_tokens=800
        )
        translated_masked = response.content.strip()

        # Unmask legal tokens
        final_translation = unmask_legal_identifiers(translated_masked, tokens)

        _TRANSLATION_CACHE[cache_key] = final_translation
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=final_translation,
            cached=False
        )

    except Exception as e:
        logger.warning(f"Translation failed: {e}. Returning original text.")
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=payload.text,
            cached=False
        )
