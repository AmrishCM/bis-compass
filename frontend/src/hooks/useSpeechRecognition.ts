import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

// BCP-47 locale mapping for Indian Languages (Digital India Bhashini Standards)
export const LANG_SPEECH_MAP: Record<string, string> = {
  en: 'en-IN',
  hi: 'hi-IN',
  ta: 'ta-IN',
  te: 'te-IN',
  kn: 'kn-IN',
  ml: 'ml-IN',
  mr: 'mr-IN',
  bn: 'bn-IN',
  gu: 'gu-IN',
  pa: 'pa-IN',
  or: 'or-IN'
};

interface UseSpeechRecognitionOptions {
  onResult?: (transcript: string) => void;
  onError?: (error: any) => void;
  preferBhashiniASR?: boolean;
}

export function useSpeechRecognition(options?: UseSpeechRecognitionOptions) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);
  const [isProcessingASR, setIsProcessingASR] = useState(false);
  const [activeEngine, setActiveEngine] = useState<'browser' | 'bhashini'>('browser');

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const hasMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    setIsSupported(!!SpeechRecognition || hasMedia);
  }, []);

  const startListening = useCallback(async (langCode: string = 'en') => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    // Browser Web Speech Recognition (Zero Latency Direct Speech)
    if (SpeechRecognition && !options?.preferBhashiniASR) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // ignore
        }
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = LANG_SPEECH_MAP[langCode] || 'en-IN';

      recognition.onstart = () => {
        setIsListening(true);
        setActiveEngine('browser');
      };

      recognition.onresult = (event: any) => {
        let currentText = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          currentText += event.results[i][0].transcript;
        }
        setTranscript(currentText);
        if (options?.onResult) {
          options.onResult(currentText);
        }
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
        if (options?.onError) {
          options.onError(event.error);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      try {
        recognition.start();
        return;
      } catch (e) {
        console.warn('Web Speech API failed to start, falling back to MediaRecorder Bhashini ASR', e);
      }
    }

    // MediaRecorder Fallback -> Send to Bhashini ASR endpoint
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          setIsListening(false);
          setIsProcessingASR(true);
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });

          // Convert to base64
          const reader = new FileReader();
          reader.readAsDataURL(audioBlob);
          reader.onloadend = async () => {
            try {
              const base64Audio = (reader.result as string).split(',')[1];
              const res = await api.transcribeAudioBhashini(base64Audio, langCode, 'wav');
              if (res && res.transcript) {
                setTranscript(res.transcript);
                if (options?.onResult) {
                  options.onResult(res.transcript);
                }
              }
            } catch (err) {
              console.error('Bhashini ASR transcription error:', err);
              if (options?.onError) options.onError(err);
            } finally {
              setIsProcessingASR(false);
            }
          };

          // Stop all audio tracks
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        setIsListening(true);
        setActiveEngine('bhashini');
      } catch (err) {
        console.error('Microphone access denied or error:', err);
        setIsListening(false);
        if (options?.onError) options.onError(err);
      }
    }
  }, [options]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // ignore
      }
      setIsListening(false);
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        // ignore
      }
      setIsListening(false);
    }
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript('');
  }, []);

  return {
    isListening,
    isProcessingASR,
    transcript,
    isSupported,
    activeEngine,
    startListening,
    stopListening,
    resetTranscript,
  };
}
