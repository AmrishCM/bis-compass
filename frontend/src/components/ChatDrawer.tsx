import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User, BookOpen, ShieldAlert, Sparkles, RefreshCw, Globe, ExternalLink, Mic, MicOff } from 'lucide-react';
import { api } from '../services/api';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useLanguage } from '../i18n/LanguageContext';

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  initialStandardId?: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  is_live_research?: boolean;
  sources_investigated?: Array<{
    url: string;
    title: string;
    authority_level: number;
  }>;
  citations?: Array<{
    standard_number: string;
    clause_number: string;
    heading: string;
    source_title: string;
    authority_level: number;
  }>;
}

export const ChatDrawer: React.FC<ChatDrawerProps> = ({ isOpen, onClose, initialStandardId }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Welcome to the BIS-Compass Compliance Advisor. Ask me anything regarding Indian Standards, certification requirements (ISI Mark, CRS), testing parameters, or accredited laboratories. Every answer is grounded in verified BIS standards.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { currentLanguage = 'en' } = useLanguage();
  const { isListening, startListening, stopListening, isSupported: isSpeechSupported } = useSpeechRecognition({
    onResult: (text) => setInput(text),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!isOpen) return null;

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input.trim();
    setInput('');
    const newMessages: Message[] = [...messages, { role: 'user', content: userText }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const response = await api.sendChatMessage(
        newMessages.map((m) => ({ role: m.role, content: m.content })),
        initialStandardId
      );

      if (response.success && response.message) {
        setMessages([
          ...newMessages,
          {
            role: 'assistant',
            content: response.message.content,
            citations: response.citations,
            is_live_research: response.is_live_research,
            sources_investigated: response.sources_investigated,
          },
        ]);
      }
    } catch (err: any) {
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: 'Error communicating with compliance engine. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 flex justify-end">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col border-l border-slate-200">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded bg-emerald-700 text-white flex items-center justify-center">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">BIS Compliance Advisor</h3>
              <p className="text-[11px] text-slate-500">Grounded in verified Gazette & Indian Standards</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Message feed */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex space-x-2.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.role === 'assistant' && (
                <div className="h-7 w-7 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="h-4 w-4" />
                </div>
              )}
              <div
                className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-emerald-700 text-white font-medium'
                    : 'bg-slate-50 text-slate-800 border border-slate-200'
                }`}
              >
                {/* Live Research Badge */}
                {m.is_live_research && (
                  <div className="mb-2 inline-flex items-center space-x-1 bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded text-[10px] font-semibold">
                    <Globe className="h-3 w-3" />
                    <span>Live Web Grounded</span>
                  </div>
                )}

                <div className="whitespace-pre-wrap">{m.content}</div>

                {/* Sources Investigated */}
                {m.sources_investigated && m.sources_investigated.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-200/60 space-y-1">
                    <span className="text-[10px] font-semibold uppercase text-slate-500 flex items-center space-x-1">
                      <Globe className="h-3 w-3 text-emerald-600 inline" />
                      <span>Live Sources Consulted:</span>
                    </span>
                    <div className="flex flex-col gap-1">
                      {m.sources_investigated.map((s, sIdx) => (
                        <a
                          key={sIdx}
                          href={s.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center text-[10px] text-emerald-700 hover:underline truncate max-w-full"
                        >
                          <ExternalLink className="h-2.5 w-2.5 mr-1 shrink-0" />
                          <span className="truncate">{s.title || s.url}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-200/60 space-y-1">
                    <span className="text-[10px] font-semibold uppercase text-slate-500 flex items-center space-x-1">
                      <BookOpen className="h-3 w-3 text-emerald-600 inline" />
                      <span>Verified Citations:</span>
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {m.citations.map((c, cIdx) => (
                        <span
                          key={cIdx}
                          className="inline-flex items-center text-[10px] bg-white border border-slate-200 rounded px-1.5 py-0.5 text-slate-700"
                        >
                          <span className="font-semibold text-emerald-700 mr-1">{c.standard_number}</span>
                          Clause {c.clause_number}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              {m.role === 'user' && (
                <div className="h-7 w-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex items-center space-x-2 text-xs text-slate-500 pl-9">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-emerald-600" />
              <span>Searching knowledge base and validating evidence...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="p-3 border-t border-slate-200 bg-white">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask about standards, testing, licensing (${(currentLanguage || 'en').toUpperCase()})...`}
              className="flex-1 border border-slate-300 rounded-md px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-emerald-600"
            />
            {isSpeechSupported && (
              <button
                type="button"
                onClick={() => {
                  if (isListening) stopListening();
                  else startListening(currentLanguage);
                }}
                className={`p-2 rounded-md border transition cursor-pointer ${
                  isListening
                    ? 'bg-rose-50 border-rose-300 text-rose-600 animate-pulse'
                    : 'border-slate-300 text-slate-500 hover:text-emerald-700 hover:bg-slate-50'
                }`}
                title="Voice Input (Speech recognition)"
              >
                {isListening ? <MicOff className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
              </button>
            )}
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white rounded-md px-3 py-2 text-xs font-semibold flex items-center space-x-1 transition cursor-pointer"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
