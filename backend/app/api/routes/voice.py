from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import base64
import logging

from app.services.bhashini import get_bhashini_service, BHASHINI_LANGUAGES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Bhashini Voice Intelligence (ASR & TTS)"])

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize into speech audio")
    language: str = Field("hi", description="Language code (hi, ta, te, kn, ml, mr, bn, gu, pa, or, en)")
    gender: Optional[str] = Field("female", description="Voice gender (female/male)")

class ASRRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio bytes")
    language: str = Field("hi", description="Spoken language code")
    audio_format: Optional[str] = Field("wav", description="Audio format (wav/mp3/ogg)")

class TranslateAndSpeakRequest(BaseModel):
    text: str = Field(..., description="Source text in English or Indian language")
    source_language: Optional[str] = Field("en", description="Source language code")
    target_language: str = Field("hi", description="Target language to translate and speak")
    gender: Optional[str] = Field("female", description="Voice gender")

@router.get("/status", summary="Check Bhashini Voice (ASR & TTS) Engine Status")
async def get_voice_status():
    """Returns the operational status and supported voice capabilities of Bhashini."""
    bhashini = get_bhashini_service()
    status = bhashini.get_status()
    return {
        **status,
        "tts_available": True,
        "asr_available": True,
        "bcp47_mapping": {code: info["bcp47"] for code, info in BHASHINI_LANGUAGES.items()}
    }

@router.post("/tts", summary="Synthesize Text to Speech using Bhashini Neural Voice")
async def synthesize_speech(payload: TTSRequest):
    """
    Synthesizes regulatory and compliance prose into natural spoken Indian language voice.
    PRIMARY: Digital India Bhashini Neural TTS.
    FALLBACK: Instructs frontend to use client-side Web Speech Synthesis with native BCP-47 voice.
    """
    lang = payload.language.lower().strip()
    if lang not in BHASHINI_LANGUAGES:
        lang = "hi"

    bhashini = get_bhashini_service()
    result = await bhashini.synthesize_speech(
        text=payload.text,
        target_lang=lang,
        gender=payload.gender or "female"
    )

    if result:
        return {
            "success": True,
            "provider": "bhashini_nltm",
            "audio_content": result["audio_content"],
            "audio_format": result.get("audio_format", "wav"),
            "language": lang,
            "fallback": False
        }

    # Graceful fallback response
    bcp47 = BHASHINI_LANGUAGES.get(lang, {}).get("bcp47", "hi-IN")
    return {
        "success": True,
        "provider": "browser_web_speech",
        "audio_content": None,
        "audio_format": None,
        "language": lang,
        "bcp47": bcp47,
        "fallback": True,
        "message": "Bhashini neural audio fallback active. Playing via browser high-quality speech synthesis."
    }

@router.post("/asr", summary="Transcribe Spoken Voice to Text using Bhashini ASR")
async def transcribe_speech(payload: ASRRequest):
    """
    Transcribes audio into text using Bhashini Speech Recognition (ASR).
    Accepts Base64 audio string.
    """
    lang = payload.language.lower().strip()
    bhashini = get_bhashini_service()

    if not bhashini.is_configured():
        return {
            "success": False,
            "transcript": "",
            "provider": "unconfigured",
            "message": "Bhashini ASR credentials not configured in backend/.env. Use browser Web Speech recognition."
        }

    transcript = await bhashini.transcribe_speech(
        audio_base64=payload.audio_base64,
        source_lang=lang,
        audio_format=payload.audio_format or "wav"
    )

    if transcript:
        return {
            "success": True,
            "transcript": transcript,
            "provider": "bhashini_nltm",
            "language": lang
        }

    return {
        "success": False,
        "transcript": "",
        "provider": "bhashini_nltm",
        "message": "Speech transcription yielded no text or timed out."
    }

@router.post("/asr/upload", summary="Transcribe Uploaded Audio File using Bhashini ASR")
async def transcribe_speech_upload(
    audio_file: UploadFile = File(...),
    language: str = Form("hi"),
    audio_format: str = Form("wav")
):
    """
    Transcribes multipart-uploaded audio file to text.
    """
    content = await audio_file.read()
    b64_audio = base64.b64encode(content).decode("utf-8")

    return await transcribe_speech(ASRRequest(
        audio_base64=b64_audio,
        language=language,
        audio_format=audio_format
    ))

@router.post("/translate-and-speak", summary="Translate text and synthesize voice in one call")
async def translate_and_speak(payload: TranslateAndSpeakRequest):
    """
    Convenience pipeline:
    1. Translates compliance text into the target Indian language.
    2. Synthesizes spoken voice audio for the translated text.
    """
    target = payload.target_language.lower().strip()
    source = (payload.source_language or "en").lower().strip()

    from app.api.routes.translate import translate_text, TranslationRequest

    # Step 1: Translate
    translation_res = await translate_text(TranslationRequest(
        text=payload.text,
        target_lang=target,
        source_lang=source
    ))
    translated_text = translation_res.translated_text

    # Step 2: Synthesize voice
    bhashini = get_bhashini_service()
    tts_result = await bhashini.synthesize_speech(
        text=translated_text,
        target_lang=target,
        gender=payload.gender or "female"
    )

    bcp47 = BHASHINI_LANGUAGES.get(target, {}).get("bcp47", "hi-IN")

    return {
        "original_text": payload.text,
        "translated_text": translated_text,
        "target_language": target,
        "bcp47": bcp47,
        "audio_content": tts_result["audio_content"] if tts_result else None,
        "audio_format": tts_result.get("audio_format", "wav") if tts_result else None,
        "provider": tts_result["provider"] if tts_result else "browser_web_speech",
        "fallback": tts_result is None
    }
