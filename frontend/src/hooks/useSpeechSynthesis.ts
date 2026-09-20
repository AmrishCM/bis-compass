import { useState, useEffect, useCallback } from 'react';
import { LANG_SPEECH_MAP } from './useSpeechRecognition';

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);

  useEffect(() => {
    setIsSupported('speechSynthesis' in window && 'SpeechSynthesisUtterance' in window);
  }, []);

  const stopSpeaking = useCallback(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const speak = useCallback((text: string, langCode: string = 'en') => {
    if (!('speechSynthesis' in window)) {
      console.warn('SpeechSynthesis is not supported in this browser.');
      return;
    }

    window.speechSynthesis.cancel();

    // Clean up markdown/special characters for speech
    const cleanText = text
      .replace(/[*#_`>]/g, '')
      .replace(/\n+/g, '. ')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const targetLang = LANG_SPEECH_MAP[langCode] || 'en-IN';
    utterance.lang = targetLang;
    utterance.rate = 0.95; // Slightly slower for clarity in regulatory technical reading

    // Try to find a matching voice
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find(
      (v) => v.lang === targetLang || v.lang.replace('_', '-').startsWith(targetLang.split('-')[0])
    );
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = (e) => {
      console.error('Speech synthesis error:', e);
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  return {
    isSpeaking,
    isSupported,
    speak,
    stopSpeaking,
  };
}
