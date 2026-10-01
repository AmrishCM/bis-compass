import pytest
import asyncio
from app.services.bhashini import get_bhashini_service, BHASHINI_LANGUAGES
from app.services.bhashini.bhashini_service import mask_legal_identifiers, unmask_legal_identifiers

def test_legal_identifier_masking():
    """Verify Rule 8.11: Technical & legal identifiers are masked verbatim and restored."""
    sample_text = (
        "According to IS 17526:2021 Clause 4.2 and Gazette Notification S.O. 123 (E), "
        "domestic stainless steel bottles must comply with Scheme I."
    )
    masked, tokens = mask_legal_identifiers(sample_text)
    
    # Assert IS standard was masked
    assert "IS 17526:2021" not in masked
    assert "__LEGAL_ID_" in masked
    
    # Assert restoration
    restored = unmask_legal_identifiers(masked, tokens)
    assert restored == sample_text

def test_bhashini_service_status():
    """Verify Bhashini integration diagnostic status returns 11 supported Indian languages."""
    bhashini = get_bhashini_service()
    status = bhashini.get_status()
    
    assert status["provider"] == "Digital India Bhashini (NLTM / MeitY)"
    assert len(status["supported_languages"]) >= 11
    assert "hi" in status["supported_languages"]
    assert "ta" in status["supported_languages"]
    assert "te" in status["supported_languages"]
    assert "kn" in status["supported_languages"]
    assert "ml" in status["supported_languages"]
    assert "mr" in status["supported_languages"]
    assert "bn" in status["supported_languages"]
    assert "gu" in status["supported_languages"]
    assert "pa" in status["supported_languages"]
    assert "or" in status["supported_languages"]
    assert status["fallback_enabled"] is True

@pytest.mark.asyncio
async def test_bhashini_voice_tts_fallback():
    """Verify Bhashini TTS returns fallback audio metadata when API credentials are mock/unconfigured."""
    bhashini = get_bhashini_service()
    res = await bhashini.synthesize_speech("नमस्ते", target_lang="hi")
    # If unconfigured in local test, returns None signaling fallback to browser speech synthesis
    if not bhashini.is_configured():
        assert res is None

def test_api_translate_and_voice_endpoints():
    """Test FastAPI routes for translation and voice status & inference."""
    from starlette.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        # 1. Translate status
        res_t_status = client.get("/api/translate/status")
        assert res_t_status.status_code == 200
        t_data = res_t_status.json()
        assert "supported_languages" in t_data
        assert "hi" in t_data["supported_languages"]

        # 2. Voice status
        res_v_status = client.get("/api/voice/status")
        assert res_v_status.status_code == 200
        v_data = res_v_status.json()
        assert v_data.get("tts_available") is True
        assert v_data.get("asr_available") is True

        # 3. Voice TTS fallback endpoint
        res_tts = client.post("/api/voice/tts", json={
            "text": "भारतीय मानक ब्यूरो प्रमाणन अनिवार्य है।",
            "language": "hi",
            "gender": "female"
        })
        assert res_tts.status_code == 200
        tts_json = res_tts.json()
        assert tts_json["success"] is True
        assert tts_json["language"] == "hi"

        # 4. Identity translation (en to en)
        res_trans_id = client.post("/api/translate", json={
            "text": "Stainless Steel Water Bottles",
            "source_lang": "en",
            "target_lang": "en"
        })
        assert res_trans_id.status_code == 200
        assert res_trans_id.json()["translated_text"] == "Stainless Steel Water Bottles"

