import { useState, useEffect, useCallback, useRef } from 'react';
import { LANG_SPEECH_MAP } from './useSpeechRecognition';
import { api } from '../services/api';

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [activeProvider, setActiveProvider] = useState<'bhashini_nltm' | 'browser'>('browser');
  const [isSupported, setIsSupported] = useState(false);

  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    setIsSupported(('speechSynthesis' in window && 'SpeechSynthesisUtterance' in window) || typeof Audio !== 'undefined');
    return () => {
      stopSpeaking();
    };
  }, []);

  const stopSpeaking = useCallback(() => {
    // Stop HTML5 Audio if playing Bhashini stream
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
      audioPlayerRef.current = null;
    }

    // Stop browser Web Speech
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    setIsSpeaking(false);
    setIsLoadingAudio(false);
  }, []);

  const speak = useCallback(async (text: string, langCode: string = 'en', preferBhashini: boolean = true) => {
    stopSpeaking();

    // Clean up markdown/special characters for speech
    const cleanText = text
      .replace(/[*#_`>]/g, '')
      .replace(/\n+/g, '. ')
      .trim();

    if (!cleanText) return;

    // 1. Try Bhashini Neural Voice if requested and non-English or selected
    if (preferBhashini) {
      setIsLoadingAudio(true);
      try {
        const ttsRes = await api.synthesizeSpeechBhashini(cleanText, langCode, 'female');
        if (ttsRes && ttsRes.success && ttsRes.audio_content && !ttsRes.fallback) {
          const mimeType = ttsRes.audio_format === 'mp3' ? 'audio/mpeg' : 'audio/wav';
          const audioUrl = `data:${mimeType};base64,${ttsRes.audio_content}`;
          const audio = new Audio(audioUrl);
          audioPlayerRef.current = audio;

          audio.onplay = () => {
            setIsSpeaking(true);
            setIsLoadingAudio(false);
            setActiveProvider('bhashini_nltm');
          };
          audio.onended = () => {
            setIsSpeaking(false);
            audioPlayerRef.current = null;
          };
          audio.onerror = () => {
            console.warn('Audio playback error, falling back to browser speech synthesis');
            setIsLoadingAudio(false);
            fallbackBrowserSpeak(cleanText, langCode);
          };

          await audio.play();
          return;
        }
      } catch (err) {
        console.warn('Bhashini TTS synthesis unavailable, seamlessly falling back to browser speech synthesis', err);
      } finally {
        setIsLoadingAudio(false);
      }
    }

    // 2. Resilient Fallback: High Quality Browser Web Speech Synthesis
    fallbackBrowserSpeak(cleanText, langCode);
  }, [stopSpeaking]);

  const fallbackBrowserSpeak = (cleanText: string, langCode: string) => {
    if (!('speechSynthesis' in window)) {
      console.warn('SpeechSynthesis is not supported in this browser.');
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    const targetLang = LANG_SPEECH_MAP[langCode] || 'en-IN';
    utterance.lang = targetLang;
    utterance.rate = 0.95; // Clear regulatory pace

    // Locate matching regional voice if available
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find(
      (v) => v.lang === targetLang || v.lang.replace('_', '-').startsWith(targetLang.split('-')[0])
    );
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
      setActiveProvider('browser');
    };
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = (e) => {
      console.error('Speech synthesis error:', e);
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  return {
    isSpeaking,
    isLoadingAudio,
    activeProvider,
    isSupported,
    speak,
    stopSpeaking,
  };
}
