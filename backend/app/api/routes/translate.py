from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import re
import logging
import asyncio

from app.services.bhashini import get_bhashini_service, BHASHINI_LANGUAGES
from app.services.bhashini.bhashini_service import mask_legal_identifiers, unmask_legal_identifiers
from app.services.llm.provider_factory import get_llm_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/translate", tags=["Multi-Language Localization & Bhashini"])

# In-memory translation cache to avoid duplicate calls
_TRANSLATION_CACHE: Dict[str, str] = {}

LANGUAGE_NAMES = {
    code: f"{info['name']} ({info['native']})" if info['native'] != info['name'] else info['name']
    for code, info in BHASHINI_LANGUAGES.items()
}

class TranslationRequest(BaseModel):
    text: str = Field(..., description="Prose, explanation, or question to translate")
    target_lang: Optional[str] = Field(None, description="Target language code: en, hi, ta, te, kn, ml, mr, bn, gu, pa, or")
    target_language: Optional[str] = Field(None, description="Alias for target_lang")
    source_lang: Optional[str] = Field("en", description="Source language code (default: en)")
    session_id: Optional[str] = None

class BatchTranslationRequest(BaseModel):
    texts: List[str] = Field(..., description="List of strings to translate")
    target_lang: str = Field(..., description="Target language code: en, hi, ta, te, kn, ml, mr, bn, gu, pa, or")
    source_lang: Optional[str] = Field("en", description="Source language code (default: en)")

class TranslationResponse(BaseModel):
    original_text: str
    target_lang: str
    translated_text: str
    cached: bool = False
    provider: str = "bhashini_nltm"

class BatchTranslationResponse(BaseModel):
    translations: List[str]
    target_lang: str
    provider: str

@router.get("/status", summary="Check Bhashini & LLM Translation Engine Status")
async def get_translation_status():
    """Returns the operational status of Bhashini and fallback translation engines."""
    bhashini = get_bhashini_service()
    status = bhashini.get_status()
    status["supported_languages_list"] = [
        {"code": code, "name": info["name"], "native": info["native"], "bcp47": info["bcp47"]}
        for code, info in BHASHINI_LANGUAGES.items()
    ]
    return status

@router.post("", response_model=TranslationResponse, summary="Translate dynamic compliance prose preserving legal identifiers")
async def translate_text(payload: TranslationRequest):
    """
    Translates dynamic compliance text (clarifications, explanations, recommendations)
    into Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, or Odia.

    PRIMARY: Digital India Bhashini (NLTM / MeitY) Neural Machine Translation.
    FALLBACK: Resilient Dual-LLM (NVIDIA + Groq) legal translator.

    NON-NEGOTIABLE RULE (Section 8.11):
    Legal and technical citations (e.g. 'IS 17526:2021', official titles, Gazette numbers,
    clause numbers, 'BIS', 'QCO', Scheme numbers) are NEVER translated or altered.
    """
    target = (payload.target_lang or payload.target_language or "en").lower().strip()
    source = (payload.source_lang or "en").lower().strip()

    if target == source or not payload.text.strip():
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=payload.text,
            cached=True,
            provider="identity"
        )

    if target not in BHASHINI_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language code '{target}'. Supported: {list(BHASHINI_LANGUAGES.keys())}"
        )

    cache_key = f"{source}:{target}:{hash(payload.text.strip())}"
    if cache_key in _TRANSLATION_CACHE:
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=_TRANSLATION_CACHE[cache_key],
            cached=True,
            provider="cache"
        )

    # Attempt Primary Provider: Bhashini NMT
    bhashini = get_bhashini_service()
    bhashini_result = await bhashini.translate(payload.text, source_lang=source, target_lang=target)
    if bhashini_result:
        _TRANSLATION_CACHE[cache_key] = bhashini_result
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=bhashini_result,
            cached=False,
            provider="bhashini_nltm"
        )

    # Resilient Fallback Provider: Dual LLM with Legal Token Masking
    masked_text, tokens = mask_legal_identifiers(payload.text)
    lang_info = BHASHINI_LANGUAGES.get(target, {"name": "English", "native": ""})
    lang_display = f"{lang_info['name']} ({lang_info['native']})" if lang_info['native'] else lang_info['name']

    llm = get_llm_provider()
    system_prompt = (
        f"You are a professional legal-regulatory translator for Indian Bureau of Indian Standards (BIS).\n"
        f"Translate the provided text accurately and naturally into {lang_display}.\n"
        f"CRITICAL RULES:\n"
        f"1. DO NOT translate, modify, or remove placeholder tokens like __LEGAL_ID_0__, __LEGAL_ID_1__, etc. Keep them exactly as they are.\n"
        f"2. Retain all technical and regulatory accuracy.\n"
        f"3. Return ONLY the translated text, no preamble, notes, or quotes."
    )

    try:
        response = await llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": masked_text}
            ],
            temperature=0.1,
            max_tokens=900
        )
        translated_masked = response.content.strip()
        final_translation = unmask_legal_identifiers(translated_masked, tokens)

        _TRANSLATION_CACHE[cache_key] = final_translation
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=final_translation,
            cached=False,
            provider="resilient_llm_fallback"
        )

    except Exception as e:
        logger.warning(f"Both Bhashini and LLM translation failed: {e}. Returning original text.")
        return TranslationResponse(
            original_text=payload.text,
            target_lang=target,
            translated_text=payload.text,
            cached=False,
            provider="original_fallback"
        )

@router.post("/batch", response_model=BatchTranslationResponse, summary="Batch translate multiple UI elements or compliance points")
async def translate_batch(payload: BatchTranslationRequest):
    """
    Translates multiple strings in a fast single-pass batch with token masking and in-memory caching.
    """
    target = payload.target_lang.lower().strip()
    source = (payload.source_lang or "en").lower().strip()

    if target == source or not payload.texts:
        return BatchTranslationResponse(
            translations=payload.texts,
            target_lang=target,
            provider="identity"
        )

    results: List[Optional[str]] = [None] * len(payload.texts)
    uncached_indices: List[int] = []

    for i, text in enumerate(payload.texts):
        if not text or not text.strip():
            results[i] = text
            continue
        cache_key = f"{source}:{target}:{hash(text.strip())}"
        if cache_key in _TRANSLATION_CACHE:
            results[i] = _TRANSLATION_CACHE[cache_key]
        else:
            uncached_indices.append(i)

    if not uncached_indices:
        return BatchTranslationResponse(
            translations=[r or "" for r in results],
            target_lang=target,
            provider="cache"
        )

    # Try Bhashini for uncached texts first
    bhashini = get_bhashini_service()
    if bhashini.is_configured():
        for idx in uncached_indices:
            t = payload.texts[idx]
            b_res = await bhashini.translate(t, source_lang=source, target_lang=target)
            if b_res:
                results[idx] = b_res
                _TRANSLATION_CACHE[f"{source}:{target}:{hash(t.strip())}"] = b_res

        uncached_indices = [idx for idx in uncached_indices if results[idx] is None]

    if not uncached_indices:
        return BatchTranslationResponse(
            translations=[r or "" for r in results],
            target_lang=target,
            provider="bhashini_nltm"
        )

    # Resilient fallback: translate remaining texts in a single bundled LLM call
    masked_items = []
    bundle_tokens = {}
    for idx in uncached_indices:
        masked, tokens = mask_legal_identifiers(payload.texts[idx])
        masked_items.append(f"[{idx}] {masked}")
        bundle_tokens[idx] = tokens

    bundled_prompt = "\n".join(masked_items)
    lang_info = BHASHINI_LANGUAGES.get(target, {"name": "English", "native": ""})
    lang_display = f"{lang_info['name']} ({lang_info['native']})" if lang_info['native'] else lang_info['name']

    llm = get_llm_provider()
    system_prompt = (
        f"You are a professional legal-regulatory translator for the Indian Bureau of Indian Standards.\n"
        f"Translate each numbered item into {lang_display}.\n"
        f"CRITICAL FORMAT RULES:\n"
        f"1. Preserve the index tag '[index]' at the start of each line.\n"
        f"2. Keep placeholder tokens like __LEGAL_ID_0__, __LEGAL_ID_1__, etc. EXACTLY as they are.\n"
        f"3. Return ONLY the translated lines with their index tags."
    )

    try:
        response = await llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": bundled_prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )

        lines = response.content.strip().split("\n")
        line_map = {}
        for line in lines:
            line_clean = line.strip()
            match = re.match(r'^\[(\d+)\]\s*(.*)$', line_clean)
            if match:
                idx = int(match.group(1))
                line_map[idx] = match.group(2)

        for idx in uncached_indices:
            raw_trans = line_map.get(idx, payload.texts[idx])
            final_trans = unmask_legal_identifiers(raw_trans, bundle_tokens.get(idx, {}))
            results[idx] = final_trans
            _TRANSLATION_CACHE[f"{source}:{target}:{hash(payload.texts[idx].strip())}"] = final_trans

        return BatchTranslationResponse(
            translations=[r or payload.texts[i] for i, r in enumerate(results)],
            target_lang=target,
            provider="resilient_llm_fallback"
        )
    except Exception as e:
        logger.warning(f"Batch LLM translation failed: {e}. Falling back to original texts.")
        for idx in uncached_indices:
            results[idx] = payload.texts[idx]

        return BatchTranslationResponse(
            translations=[r or payload.texts[i] for i, r in enumerate(results)],
            target_lang=target,
            provider="original_fallback"
        )
