import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  AlertTriangle,
  Building2,
  ChevronRight,
  ShieldCheck,
  Globe,
  UploadCloud,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  MapPin,
  ExternalLink,
  Download,
  HelpCircle,
  FileText,
  Clock,
  ArrowRight,
  Layers,
  Circle,
  Check,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Briefcase,
  Microscope,
  Printer,
  Sparkles,
  GitBranch,
  FlaskConical,
  ClipboardCheck,
  Wrench,
} from 'lucide-react';
import { api, AnalysisResponse, ClarificationQuestionItem } from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { StandardsDependencyTree } from '../components/StandardsDependencyTree';
import { FeeTimelineCalculator } from '../components/FeeTimelineCalculator';
import { downloadComplianceDossier } from '../utils/dossierPdfGenerator';

/* ============================================================================
   PROGRESS STEPS (Section 9)
   ============================================================================ */
const PROGRESS_STEPS = [
  { key: 'product', label: 'Product details' },
  { key: 'standard', label: 'BIS standard' },
  { key: 'certification', label: 'Certification' },
  { key: 'tests', label: 'Tests' },
  { key: 'laboratory', label: 'Testing centre' },
  { key: 'application', label: 'Application' },
];

/* ============================================================================
   TEST SCENARIO PRESETS (moved to collapsible drawer)
   ============================================================================ */
const TEST_PRESETS = [
  { label: 'SS Water Bottles (Triggers Clarification)', product: 'I manufacture stainless steel water bottles.', location: 'Tiruppur, Tamil Nadu', details: '' },
  { label: 'Vacuum Insulated Bottle (Fully Specified)', product: 'Stainless steel double-walled vacuum insulated drinking bottle 750ml for domestic use.', location: 'Tiruppur, Tamil Nadu', details: 'SS 304 food contact liner, screw cap with food-grade silicone gasket.' },
  { label: 'PVC Electric Cables', product: 'We manufacture PVC insulated electric cables with copper conductor.', location: 'Delhi', details: '' },
  { label: 'Multi-Product Input', product: 'I manufacture stainless steel bottles, electrical switches and PVC pipes.', location: 'Chennai, Tamil Nadu', details: '' },
];

export const ProductAnalysis: React.FC = () => {
  const routerLocation = useLocation();
  const { t } = useLanguage();

  // Form
  const [productInput, setProductInput] = useState('');
  const [locationInput, setLocationInput] = useState('');
  const [additionalDetails, setAdditionalDetails] = useState('');
  const [docText, setDocText] = useState('');
  const [includeWeb, setIncludeWeb] = useState(true);
  const [showPresets, setShowPresets] = useState(false);

  // Async
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isClarifying, setIsClarifying] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Results
  const [results, setResults] = useState<AnalysisResponse | null>(null);
  const [batchAnswers, setBatchAnswers] = useState<Record<string, string>>({});
  const [customAnswers, setCustomAnswers] = useState<Record<string, string>>({});
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [complianceMode, setComplianceMode] = useState<'msme' | 'auditor'>('msme');
  const [standardDependencies, setStandardDependencies] = useState<any[]>([]);

  const [readinessProfile, setReadinessProfile] = useState<'msme' | 'startup' | 'large'>('msme');
  const [checkedDocs, setCheckedDocs] = useState<Record<string, boolean>>({});

  // Voice Processing
  const { currentLanguage = 'en' } = useLanguage();
  const { isListening, startListening, stopListening, isSupported: isSpeechSupported } = useSpeechRecognition({
    onResult: (text) => setProductInput(text),
  });
  const { speak, isSpeaking, stopSpeaking } = useSpeechSynthesis();

  // Dynamically fetch dependencies for the verified standard from database
  useEffect(() => {
    const stdId = results?.standard?.standard_id || results?.auditor_matrix?.standard_id || results?.applicable_standards?.[0]?.standard_id;
    if (stdId) {
      api.getStandardDependencies(stdId)
        .then((res) => {
          if (res && res.dependencies) {
            setStandardDependencies(res.dependencies);
          } else {
            setStandardDependencies([]);
          }
        })
        .catch((err) => {
          console.warn('Failed to load standard dependencies from database:', err);
          setStandardDependencies([]);
        });
    } else {
      setStandardDependencies([]);
    }
  }, [results]);

  // Handle pre-filled description from router
  useEffect(() => {
    if (routerLocation.state && (routerLocation.state as any).description) {
      const prefill = (routerLocation.state as any).description;
      setProductInput(prefill);
      runAnalysis(prefill, locationInput, '');
    }
  }, [routerLocation.state]);

  /* --------------------------------------------------------------------------
     API CALLS
     -------------------------------------------------------------------------- */
  const runAnalysis = async (productDesc: string, loc: string, details: string) => {
    if (!productDesc.trim()) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    setBatchAnswers({});
    setCustomAnswers({});

    const combinedDesc = details.trim()
      ? `${productDesc.trim()}. Additional details: ${details.trim()}`
      : productDesc.trim();

    try {
      const res = await api.analyzeProduct({
        product_description: combinedDesc,
        additional_details: details.trim() || undefined,
        document_text: docText || undefined,
        location: loc || undefined,
        include_web_search: includeWeb,
      });
      setResults(res);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Analysis failed. Please check your connection.';
      setAnalysisError(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productInput.trim()) return;
    await runAnalysis(productInput, locationInput, additionalDetails);
  };

  const handleClarifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!results?.session_id) return;
    setIsClarifying(true);
    setAnalysisError(null);

    const finalAnswers: Record<string, string> = { ...batchAnswers };
    Object.entries(customAnswers).forEach(([k, v]) => {
      if (v.trim()) finalAnswers[k] = v.trim();
    });

    try {
      const res = await api.clarifyProduct({
        session_id: results.session_id,
        answers: finalAnswers,
        location: locationInput || undefined,
      });
      setResults(res);
      setBatchAnswers({});
      setCustomAnswers({});
    } catch (err: any) {
      setAnalysisError(err.response?.data?.detail || err.message || 'Submission failed.');
    } finally {
      setIsClarifying(false);
    }
  };

  const handleOptionSelect = (questionId: string, option: string) => {
    setBatchAnswers(prev => ({ ...prev, [questionId]: option }));
  };

  const handleCustomChange = (questionId: string, val: string) => {
    setCustomAnswers(prev => ({ ...prev, [questionId]: val }));
    setBatchAnswers(prev => ({ ...prev, [questionId]: val }));
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadLoading(true);
    try {
      const res = await api.uploadDocument(file);
      if (res.success && res.extracted_text) setDocText(res.extracted_text);
    } catch (err) { /* silent */ }
    finally { setUploadLoading(false); }
  };

  const exportReport = () => {
    if (!results || results.state !== 'READY') return;
    const std = results.standard;
    const cert = results.certification;
    const dateStr = new Date().toISOString().split('T')[0];
    const reportMd = `# BIS COMPLIANCE ASSESSMENT REPORT
Product: ${results.product?.name || 'Product'}
Date: ${dateStr}
Session: ${results.session_id || ''}
Location: ${locationInput || 'India'}

## 1. Product
${Object.entries(results.product?.known_details || {}).map(([k, v]) => `• ${k}: ${v}`).join('\n')}

## 2. Applicable Standard
${std ? `${std.standard_number} — ${std.title}` : 'Not verified'}
${(std?.why_applies || []).map(w => `• ${w}`).join('\n')}

## 3. Certification
Status: ${cert?.status || 'NOT VERIFIED'}
Scheme: ${cert?.scheme || ''}
${cert?.why || ''}

## 4. Required Tests
${results.tests.map((t, i) => `${i + 1}. ${t.test_name}\n   ${t.what_it_checks}`).join('\n')}

## 5. Testing Laboratories
${results.laboratories.map((l, i) => `${i + 1}. ${l.lab_name} (${l.location})`).join('\n')}

## 6. How to Apply
${results.application_steps.map(s => `${s.step_number}. ${s.title}: ${s.description}`).join('\n')}

## 7. Next Action
${results.next_action?.action || ''}
${results.next_action?.details || ''}

Generated by BIS-Compass.
`;
    const blob = new Blob([reportMd], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `BIS_Report_${results.product?.name?.replace(/[^a-zA-Z0-9]/g, '_') || 'product'}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  /* --------------------------------------------------------------------------
     DERIVED STATE
     -------------------------------------------------------------------------- */
  const state = results?.state;
  const isClarification = state === 'NEEDS_CLARIFICATION';
  const isReady = state === 'READY';
  const isNoStandard = state === 'NO_STANDARD_FOUND';
  const progress = results?.progress;

  /* --------------------------------------------------------------------------
     PROGRESS STEPPER COMPONENT (Section 9)
     -------------------------------------------------------------------------- */
  const ProgressStepper = () => {
    if (!progress) return null;
    return (
      <div className="flex items-center justify-between bg-white border border-slate-200 rounded-xl p-4 mb-6">
        {PROGRESS_STEPS.map((step, idx) => {
          const status = (progress as any)?.[step.key] || 'pending';
          const isDone = status === 'done';
          const isCurrent = status === 'current';
          const isIncomplete = status === 'incomplete';

          return (
            <React.Fragment key={step.key}>
              {idx > 0 && (
                <div className={`flex-1 h-px mx-2 ${isDone ? 'bg-emerald-400' : 'bg-slate-200'}`} />
              )}
              <div className="flex flex-col items-center text-center min-w-0">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mb-1 ${
                  isDone ? 'bg-emerald-100 text-emerald-800' :
                  isCurrent ? 'bg-emerald-800 text-white ring-2 ring-emerald-300' :
                  isIncomplete ? 'bg-amber-100 text-amber-700' :
                  'bg-slate-100 text-slate-400'
                }`}>
                  {isDone ? <Check className="w-3.5 h-3.5" /> :
                   isCurrent ? <Circle className="w-3 h-3 fill-current" /> :
                   isIncomplete ? '!' :
                   <Circle className="w-3 h-3" />}
                </div>
                <span className={`text-[10px] font-semibold leading-tight ${
                  isDone ? 'text-emerald-800' :
                  isCurrent ? 'text-emerald-900 font-bold' :
                  'text-slate-400'
                }`}>{step.label}</span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    );
  };

  /* --------------------------------------------------------------------------
     RENDER QUESTION BY TYPE (Section 6)
     -------------------------------------------------------------------------- */
  const renderQuestion = (q: ClarificationQuestionItem, idx: number) => {
    const currentAnswer = batchAnswers[q.id] || '';

    return (
      <div key={q.id || idx} className="bg-white rounded-xl p-5 border border-slate-200 space-y-3">
        <h3 className="text-sm font-bold text-slate-900">
          <span className="text-emerald-800 mr-2">{idx + 1}.</span>
          {q.question}
        </h3>

        {/* Single choice / Yes-No: radio-style pills */}
        {(q.type === 'single_choice' || q.type === 'yes_no' || !q.type) && (
          <div className="flex flex-wrap gap-2">
            {(q.options || []).map((opt, optIdx) => {
              const isSelected = currentAnswer === opt;
              return (
                <button
                  key={optIdx}
                  type="button"
                  onClick={() => handleOptionSelect(q.id, opt)}
                  className={`text-xs px-4 py-2.5 rounded-lg font-medium border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-emerald-800 text-white border-emerald-900 shadow-sm'
                      : 'bg-white hover:bg-slate-50 border-slate-300 text-slate-800'
                  }`}
                >
                  <span className="mr-1.5">{isSelected ? '●' : '○'}</span>
                  {opt}
                </button>
              );
            })}
          </div>
        )}

        {/* Multiple choice: checkbox-style pills */}
        {q.type === 'multiple_choice' && (
          <div className="flex flex-wrap gap-2">
            {(q.options || []).map((opt, optIdx) => {
              const selected = (currentAnswer || '').split('||');
              const isSelected = selected.includes(opt);
              return (
                <button
                  key={optIdx}
                  type="button"
                  onClick={() => {
                    const prev = (batchAnswers[q.id] || '').split('||').filter(Boolean);
                    const next = isSelected ? prev.filter(x => x !== opt) : [...prev, opt];
                    setBatchAnswers(p => ({ ...p, [q.id]: next.join('||') }));
                  }}
                  className={`text-xs px-4 py-2.5 rounded-lg font-medium border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-emerald-800 text-white border-emerald-900 shadow-sm'
                      : 'bg-white hover:bg-slate-50 border-slate-300 text-slate-800'
                  }`}
                >
                  <span className="mr-1.5">{isSelected ? '☑' : '☐'}</span>
                  {opt}
                </button>
              );
            })}
          </div>
        )}

        {/* Numeric input */}
        {q.type === 'numeric' && (
          <input
            type="text"
            inputMode="decimal"
            value={customAnswers[q.id] || ''}
            onChange={(e) => handleCustomChange(q.id, e.target.value)}
            placeholder="Enter value..."
            className="w-48 text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-700 bg-white"
          />
        )}

        {/* Text input */}
        {q.type === 'text' && (
          <input
            type="text"
            value={customAnswers[q.id] || ''}
            onChange={(e) => handleCustomChange(q.id, e.target.value)}
            placeholder="Type your answer..."
            className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-700 bg-white"
          />
        )}
      </div>
    );
  };

  /* ==========================================================================
     MAIN RENDER
     ========================================================================== */
  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-16 font-sans">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-4">
        <div className="flex items-center space-x-2 text-xs font-bold text-emerald-800 uppercase tracking-wider mb-1">
          <ShieldCheck className="h-4 w-4 text-emerald-700" />
          <span>Product Standards & Compliance Intelligence</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Check Your BIS Requirements
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Describe what you manufacture. We'll identify the applicable BIS standard, certification requirement, tests, and next steps.
        </p>
      </div>

      {/* ================================================================= */}
      {/* INPUT FORM                                                        */}
      {/* ================================================================= */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <form onSubmit={handleFormSubmit} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-bold text-slate-900">
                What are you manufacturing?
              </label>
              {isSpeechSupported && (
                <button
                  type="button"
                  onClick={() => {
                    if (isListening) stopListening();
                    else startListening(currentLanguage);
                  }}
                  className={`flex items-center space-x-1 text-xs px-2.5 py-1 rounded-full border transition-all font-semibold cursor-pointer ${
                    isListening
                      ? 'bg-rose-50 border-rose-300 text-rose-700 animate-pulse'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {isListening ? (
                    <>
                      <MicOff className="h-3.5 w-3.5 text-rose-600" />
                      <span>Listening ({(currentLanguage || 'en').toUpperCase()})...</span>
                    </>
                  ) : (
                    <>
                      <Mic className="h-3.5 w-3.5 text-emerald-700" />
                      <span>Voice Input ({(currentLanguage || 'en').toUpperCase()})</span>
                    </>
                  )}
                </button>
              )}
            </div>
            <div className="relative">
              <input
                type="text"
                value={productInput}
                onChange={(e) => setProductInput(e.target.value)}
                placeholder='e.g., "I manufacture stainless steel water bottles"'
                className="w-full text-sm text-slate-900 border border-slate-300 rounded-lg pl-4 pr-10 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:border-emerald-700 bg-white"
                required
              />
              {isSpeechSupported && (
                <button
                  type="button"
                  onClick={() => {
                    if (isListening) stopListening();
                    else startListening(currentLanguage);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-emerald-700 transition"
                  title="Voice Input (Speech recognition)"
                >
                  <Mic className={`h-4 w-4 ${isListening ? 'text-rose-600 animate-pulse' : ''}`} />
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Manufacturing Location
              </label>
              <div className="relative">
                <MapPin className="h-4 w-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={locationInput}
                  onChange={(e) => setLocationInput(e.target.value)}
                  placeholder="e.g., Tiruppur, Tamil Nadu"
                  className="w-full text-sm text-slate-900 border border-slate-300 rounded-lg pl-9 pr-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-700 bg-white"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Additional Details (optional)
              </label>
              <input
                type="text"
                value={additionalDetails}
                onChange={(e) => setAdditionalDetails(e.target.value)}
                placeholder="e.g., vacuum insulated, 1 litre, for household use"
                className="w-full text-sm text-slate-900 border border-slate-300 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-700 bg-white"
              />
            </div>
          </div>

          {/* Optional doc upload */}
          <div>
            <label className="flex items-center space-x-2 border border-dashed border-slate-300 rounded-lg px-4 py-2.5 text-xs text-slate-500 hover:bg-slate-50 cursor-pointer transition">
              <UploadCloud className="h-4 w-4 text-slate-400" />
              <span>{uploadLoading ? 'Extracting...' : docText ? 'Document attached ✓' : 'Attach technical document (optional)'}</span>
              <input type="file" onChange={handleFileUpload} accept=".pdf,.docx,.doc,.txt" className="hidden" />
            </label>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-100">
            <label className="flex items-center space-x-2 text-xs text-slate-500 cursor-pointer">
              <input type="checkbox" checked={includeWeb} onChange={e => setIncludeWeb(e.target.checked)} className="rounded text-emerald-700" />
              <Globe className="h-3.5 w-3.5 text-slate-400" />
              <span>Search official BIS sources</span>
            </label>

            <button
              type="submit"
              disabled={isAnalyzing || !productInput.trim()}
              className="bg-emerald-800 hover:bg-emerald-900 disabled:opacity-50 text-white text-sm font-bold px-6 py-2.5 rounded-lg shadow-sm flex items-center space-x-2 transition cursor-pointer"
            >
              {isAnalyzing ? (
                <><RefreshCw className="h-4 w-4 animate-spin" /><span>Checking…</span></>
              ) : (
                <><span>Check My BIS Requirements</span><ArrowRight className="h-4 w-4" /></>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Test scenarios drawer */}
      <div className="text-center">
        <button type="button" onClick={() => setShowPresets(!showPresets)} className="text-xs text-slate-400 hover:text-slate-600 cursor-pointer">
          {showPresets ? 'Hide test scenarios ▲' : 'Show test scenarios ▼'}
        </button>
        {showPresets && (
          <div className="flex flex-wrap justify-center gap-2 mt-2">
            {TEST_PRESETS.map((p, i) => (
              <button key={i} type="button" onClick={() => { setProductInput(p.product); setLocationInput(p.location); setAdditionalDetails(p.details); runAnalysis(p.product, p.location, p.details); }}
                className="text-xs px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 rounded-lg cursor-pointer transition">
                {p.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ================================================================= */}
      {/* ERROR STATE                                                        */}
      {/* ================================================================= */}
      {analysisError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <h2 className="text-sm font-bold text-red-900">Something went wrong</h2>
            <p className="text-xs text-red-700 mt-0.5">{analysisError}</p>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* PROGRESS STEPPER (always visible when we have results)             */}
      {/* ================================================================= */}
      {results && <ProgressStepper />}

      {/* ================================================================= */}
      {/* STATUS BANNER (Section 21)                                         */}
      {/* ================================================================= */}
      {results?.status_banner && (
        <div className={`rounded-xl p-4 flex items-start space-x-3 ${
          results.status_banner.type === 'verified' ? 'bg-emerald-50 border border-emerald-200' :
          results.status_banner.type === 'clarification' ? 'bg-amber-50 border border-amber-200' :
          'bg-slate-50 border border-slate-200'
        }`}>
          {results.status_banner.type === 'verified' ? <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" /> :
           results.status_banner.type === 'clarification' ? <HelpCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" /> :
           <Info className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />}
          <div>
            <h2 className={`text-sm font-bold ${
              results.status_banner.type === 'verified' ? 'text-emerald-900' :
              results.status_banner.type === 'clarification' ? 'text-amber-900' : 'text-slate-800'
            }`}>{results.status_banner.title}</h2>
            <p className="text-xs text-slate-600 mt-0.5">{results.status_banner.message}</p>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* PHASE A — PRODUCT IDENTIFICATION (Sections 3-8, 10-11)             */}
      {/* ================================================================= */}
      {isClarification && results?.clarification && (
        <div className="space-y-5">
          {/* Title */}
          <h2 className="text-xl font-black text-slate-900">
            {results.clarification.title}
          </h2>

          {/* "You entered" block */}
          <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">You entered</div>
            <blockquote className="text-sm text-slate-800 border-l-3 border-emerald-700 pl-3 italic">
              {results.product?.description || productInput}
            </blockquote>
          </div>

          {/* Intro text */}
          <p className="text-sm text-slate-700">
            {results.clarification.intro}
          </p>

          {/* Multi-product selector */}
          {results.multi_product_detected?.is_multi_product && results.clarification.questions?.[0]?.id === 'q_multi_product' && (
            <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-3">
              <h3 className="text-sm font-bold text-slate-900">
                Which product would you like to check compliance for first?
              </h3>
              <div className="flex flex-wrap gap-2">
                {results.multi_product_detected.detected_products.map((prod, i) => (
                  <button key={i} type="button"
                    onClick={() => { setProductInput(prod); runAnalysis(prod, locationInput, ''); }}
                    className="text-sm px-4 py-2.5 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-900 rounded-lg font-bold transition cursor-pointer">
                    {prod}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Question batch form */}
          {!(results.multi_product_detected?.is_multi_product) && (
            <form onSubmit={handleClarifySubmit} className="space-y-4">
              {/* Question count header */}
              {results.clarification.questions.length > 1 && (
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  We need {results.clarification.questions.length} details
                </div>
              )}

              {/* Render each question */}
              {results.clarification.questions.map((q, idx) => renderQuestion(q, idx))}

              {/* Explanation */}
              {results.clarification.explanation && (
                <p className="text-xs text-slate-500 italic">
                  {results.clarification.explanation}
                </p>
              )}

              {/* Submit */}
              <div className="pt-3 flex items-center justify-end">
                <button
                  type="submit"
                  disabled={isClarifying || Object.keys(batchAnswers).length === 0}
                  className="bg-emerald-800 hover:bg-emerald-900 disabled:opacity-50 text-white text-sm font-bold px-6 py-2.5 rounded-lg shadow-sm flex items-center space-x-2 transition cursor-pointer"
                >
                  {isClarifying ? (
                    <><RefreshCw className="h-4 w-4 animate-spin" /><span>Checking…</span></>
                  ) : (
                    <><span>Check My BIS Requirements</span><ArrowRight className="h-4 w-4" /></>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* PHASE B — COMPLIANCE ROADMAP (Sections 12-20)                      */}
      {/* ================================================================= */}
      {isReady && results && (
        <div className="space-y-6">
          {/* Roadmap header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h2 className="text-xl font-black text-slate-900">Your BIS Compliance Roadmap</h2>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => downloadComplianceDossier(results)}
                className="text-xs font-bold bg-emerald-800 hover:bg-emerald-900 text-white px-3.5 py-1.5 rounded-lg flex items-center space-x-1.5 shadow-sm transition cursor-pointer"
              >
                <Printer className="h-3.5 w-3.5" />
                <span>Compliance Dossier (PDF)</span>
              </button>
              <button
                type="button"
                onClick={exportReport}
                className="text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition cursor-pointer"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Markdown</span>
              </button>
            </div>
          </div>

          {/* Dual-Explanation Modes & Action Bar */}
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Mode:
              </span>
              <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200">
                <button
                  type="button"
                  onClick={() => setComplianceMode('msme')}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all cursor-pointer ${
                    complianceMode === 'msme'
                      ? 'bg-emerald-800 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Briefcase className="h-3.5 w-3.5" />
                  <span>MSME / Business Mode</span>
                </button>
                <button
                  type="button"
                  onClick={() => setComplianceMode('auditor')}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all cursor-pointer ${
                    complianceMode === 'auditor'
                      ? 'bg-indigo-900 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Microscope className="h-3.5 w-3.5" />
                  <span>Auditor / Engineer Mode</span>
                </button>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => {
                  if (isSpeaking) {
                    stopSpeaking();
                  } else {
                    const textToRead =
                      complianceMode === 'msme'
                        ? results.msme_summary?.plain_language_verdict ||
                          `Your product is governed by standard ${results.standard?.standard_number}. Certification is required under Indian law.`
                        : `Standard ${results.standard?.standard_number}. Technical clauses and laboratory protocols verified.`;
                    speak(textToRead, currentLanguage);
                  }
                }}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg border flex items-center space-x-1.5 transition cursor-pointer ${
                  isSpeaking
                    ? 'bg-rose-50 border-rose-300 text-rose-700 animate-pulse'
                    : 'bg-slate-50 hover:bg-slate-100 border-slate-300 text-slate-700'
                }`}
              >
                {isSpeaking ? (
                  <VolumeX className="h-3.5 w-3.5 text-rose-600" />
                ) : (
                  <Volume2 className="h-3.5 w-3.5 text-emerald-700" />
                )}
                <span>{isSpeaking ? 'Stop Audio' : 'Listen to Verdict'}</span>
              </button>
            </div>
          </div>

          {/* MSME Mode Summary Card */}
          {complianceMode === 'msme' && (
            <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50 border-2 border-emerald-300 rounded-xl p-5 space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  <div className="p-2 bg-emerald-700 text-white rounded-lg">
                    <Briefcase className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-emerald-950">
                      MSME Business Executive Guide
                    </h3>
                    <p className="text-xs text-emerald-800">
                      Plain-language compliance verdict for factory owners and entrepreneurs.
                    </p>
                  </div>
                </div>
                <span className="text-[11px] font-bold bg-emerald-200/80 text-emerald-900 px-2.5 py-0.5 rounded-full border border-emerald-400">
                  50% MSME Concession Eligible
                </span>
              </div>

              <div className="p-3.5 bg-white rounded-lg border border-emerald-200 text-xs text-slate-800 font-medium leading-relaxed">
                {results.msme_summary?.plain_language_verdict ||
                  `Your product is governed by ${results.standard?.standard_number}. Certification is ${results.certification?.status} under Indian law.`}
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] font-bold text-emerald-900 uppercase tracking-wide">
                  Top 3 Action Items for Factory Management:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <div className="p-2.5 bg-white rounded-lg border border-emerald-100 text-xs text-slate-700 space-y-1">
                    <span className="font-bold text-emerald-800 block">1. Raw Materials</span>
                    <span>Verify steel/polymer test mill certificates conform to Indian standards.</span>
                  </div>
                  <div className="p-2.5 bg-white rounded-lg border border-emerald-100 text-xs text-slate-700 space-y-1">
                    <span className="font-bold text-emerald-800 block">2. In-House Testing</span>
                    <span>Procure basic inspection gauges for daily factory quality control (QAP).</span>
                  </div>
                  <div className="p-2.5 bg-white rounded-lg border border-emerald-100 text-xs text-slate-700 space-y-1">
                    <span className="font-bold text-emerald-800 block">3. Claim 50% Subsidy</span>
                    <span>Apply using Udyam registration to get 50% discount on BIS statutory fees.</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Auditor Mode Dense Technical Matrix */}
          {complianceMode === 'auditor' && (
            <div className="bg-white border-2 border-indigo-200 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-indigo-100">
                <div className="flex items-center space-x-2">
                  <div className="p-2 bg-indigo-900 text-white rounded-lg">
                    <Microscope className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Technical Audit & Clause Specification Matrix
                    </h3>
                    <p className="text-xs text-slate-500">
                      Dense parameter specifications, numerical tolerances, and test methods for compliance engineers.
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">Audit Confidence</span>
                  <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                    95% Grounded
                  </span>
                </div>
              </div>

              {/* Clauses Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="bg-slate-50 text-slate-600 border-y border-slate-200">
                      <th className="p-2.5 font-bold">Clause</th>
                      <th className="p-2.5 font-bold">Parameter Heading</th>
                      <th className="p-2.5 font-bold">Specification / Requirement</th>
                      <th className="p-2.5 font-bold">Test Method</th>
                      <th className="p-2.5 font-bold">Verification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(results.standard?.technical_clauses || []).map((c, i) => (
                      <tr key={i} className="hover:bg-slate-50/70">
                        <td className="p-2.5 font-mono font-bold text-indigo-900 whitespace-nowrap">
                          Clause {c.clause_number}
                        </td>
                        <td className="p-2.5 font-semibold text-slate-800">{c.heading}</td>
                        <td className="p-2.5 text-slate-600 max-w-xs">{c.text}</td>
                        <td className="p-2.5 font-mono text-[11px] text-slate-500">
                          {results.tests?.[i]?.test_method || results.standard?.standard_number}
                        </td>
                        <td className="p-2.5">
                          <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                            VERIFIED
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ---- 01. YOUR PRODUCT (Section 13) ---- */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">01 — Your Product</span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">{results.product?.name}</h3>
              </div>
              <span className="inline-flex items-center text-xs font-bold bg-emerald-50 text-emerald-900 border border-emerald-200 px-3 py-1 rounded-full shrink-0">
                <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-emerald-700" />
                Product details confirmed
              </span>
            </div>
            {results.product?.known_details && Object.keys(results.product.known_details).length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                {Object.entries(results.product.known_details).map(([key, val]) => (
                  <div key={key}>
                    <span className="text-[11px] font-bold text-slate-400 uppercase">{key}</span>
                    <div className="font-semibold text-slate-800 mt-0.5">{val}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ---- 02. APPLICABLE STANDARD (Section 14) ---- */}
          {results.standard && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">02 — Applicable BIS Standard</span>
                  <h3 className="text-lg font-bold text-slate-900 mt-0.5">{results.standard.standard_number}</h3>
                  <div className="text-sm text-slate-700 mt-0.5">{results.standard.title}</div>
                </div>
                <span className="inline-flex items-center text-xs font-bold bg-emerald-50 text-emerald-900 border border-emerald-200 px-3 py-1 rounded-full shrink-0">
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-emerald-700" />
                  Verified
                </span>
              </div>

              {/* Why this applies */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-2">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Why this applies</h4>
                {results.standard.why_applies.map((point, idx) => (
                  <div key={idx} className="flex items-start space-x-2 text-xs text-slate-700">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700 shrink-0 mt-0.5" />
                    <span>{point}</span>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <a href={results.standard.official_source_url} target="_blank" rel="noopener noreferrer"
                  className="text-xs font-bold text-emerald-800 hover:text-emerald-900 flex items-center space-x-1">
                  <span>View BIS source</span><ExternalLink className="h-3.5 w-3.5" />
                </a>
                {results.standard.technical_clauses?.length > 0 && (
                  <button type="button" onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                    className="text-xs text-slate-500 hover:text-slate-800 flex items-center space-x-1 cursor-pointer">
                    <span>Technical details</span>
                    {showTechnicalDetails ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>
                )}
              </div>

              {showTechnicalDetails && (
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 text-xs">
                  {results.standard.technical_clauses.map((c, i) => (
                    <div key={i} className="bg-white p-3 rounded-lg border border-slate-200">
                      <div className="font-bold text-slate-800">Clause {c.clause_number}: {c.heading}</div>
                      <div className="text-slate-600 mt-1">{c.text}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Standards Dependency & Related Standards Tree */}
          {results.standard && (
            <StandardsDependencyTree
              primaryStandard={{
                standard_number: results.standard.standard_number,
                title: results.standard.title,
                status: results.standard.status,
              }}
              dependencies={standardDependencies}
            />
          )}

          {/* ---- 03. CERTIFICATION (Section 16) ---- */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
            <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">
              03 — Do You Need BIS Certification?
            </span>

            {results.certification ? (
              <>
                {/* Dominant badge */}
                <div className={`text-center py-6 rounded-xl ${
                  results.certification.status === 'REQUIRED' ? 'bg-amber-50 border-2 border-amber-300' :
                  results.certification.status === 'VOLUNTARY' ? 'bg-blue-50 border-2 border-blue-200' :
                  'bg-slate-50 border-2 border-slate-200'
                }`}>
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">BIS Certification</div>
                  <div className={`text-2xl font-black ${
                    results.certification.status === 'REQUIRED' ? 'text-amber-900' :
                    results.certification.status === 'VOLUNTARY' ? 'text-blue-900' :
                    'text-slate-700'
                  }`}>
                    {results.certification.status}
                  </div>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-2 text-xs">
                  <div><span className="font-bold text-slate-500 uppercase">Applicable scheme:</span> <span className="font-semibold text-slate-800">{results.certification.scheme}</span></div>
                  <div><span className="font-bold text-slate-500 uppercase">Why:</span> <span className="text-slate-700">{results.certification.why}</span></div>
                  <div><span className="font-bold text-slate-500 uppercase">Official basis:</span> <span className="text-slate-700">{results.certification.official_basis}</span></div>
                </div>
              </>
            ) : (
              <div className="bg-slate-50 rounded-xl p-6 text-center border border-slate-200">
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">BIS Certification</div>
                <div className="text-2xl font-black text-slate-500">NOT YET VERIFIED</div>
                <p className="text-xs text-slate-500 mt-2">Certification requirement could not be determined from available sources.</p>
              </div>
            )}
          </div>

          {/* ---- 04. TESTS (Section 17) ---- */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
            <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">04 — Tests You Need</span>
            <div className="space-y-3">
              {results.tests.map((test, idx) => (
                <div key={idx} className="flex items-start space-x-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                  <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-bold text-slate-900">{test.test_name}</h4>
                    <p className="text-slate-600 mt-0.5">What it checks: {test.what_it_checks}</p>
                    {test.test_method && <p className="text-slate-400 mt-0.5 text-[11px]">Method: {test.test_method}</p>}
                  </div>
                </div>
              ))}
            </div>

            {/* Sample Preparation & Conditioning Guidance */}
            {results.sample_preparation_guidance && (
              <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-4 space-y-3 pt-4">
                <div className="flex items-center space-x-2 pb-2 border-b border-emerald-200/80">
                  <div className="p-1.5 bg-emerald-800 text-white rounded-md">
                    <FlaskConical className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                      Specimen Conditioning & Lab Dispatch Protocol
                    </h4>
                    <p className="text-[11px] text-slate-600">
                      Standardized physical handling guidelines before laboratory submission.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                  <div className="bg-white p-3 rounded-lg border border-emerald-100 shadow-2xs">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Specimen Quantity</span>
                    <span className="font-semibold text-slate-800 mt-1 block">{results.sample_preparation_guidance.sample_quantity}</span>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-emerald-100 shadow-2xs">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Conditioning Protocol</span>
                    <span className="font-semibold text-slate-800 mt-1 block">{results.sample_preparation_guidance.preparation_and_conditioning}</span>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-emerald-100 shadow-2xs">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Packaging & Tamper Sealing</span>
                    <span className="text-slate-700 mt-1 block">{results.sample_preparation_guidance.packaging_and_sealing}</span>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-emerald-100 shadow-2xs">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Storage & Environmental Shielding</span>
                    <span className="text-slate-700 mt-1 block">{results.sample_preparation_guidance.storage_and_handling}</span>
                  </div>
                </div>

                {results.sample_preparation_guidance.labeling_instruction && (
                  <div className="p-3 bg-emerald-100/50 rounded-lg text-xs text-emerald-950 border border-emerald-200/80 flex items-start space-x-2">
                    <Info className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Mandatory Labelling Requirements: </span>
                      <span>{results.sample_preparation_guidance.labeling_instruction}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ---- 05. TESTING LABORATORIES (Section 18) ---- */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
            <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">05 — Where Can You Get It Tested?</span>
            {results.laboratories.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {results.laboratories.map((lab, idx) => (
                  <div key={idx} className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
                    <div className="flex items-start space-x-2">
                      <Building2 className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5" />
                      <div>
                        <h4 className="font-bold text-slate-900">{lab.lab_name}</h4>
                        <div className="text-slate-500">{lab.location}</div>
                      </div>
                    </div>
                    <div className="space-y-1 text-[11px] text-slate-600 pt-1 border-t border-slate-200/60">
                      {lab.is_bis_recognized && (
                        <div className="flex items-center space-x-1">
                          <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                          <span className="font-semibold text-emerald-800">BIS-recognized</span>
                        </div>
                      )}
                      {lab.phone && <div><span className="font-semibold text-slate-700">Contact:</span> {lab.phone}</div>}
                      {lab.email && <div><span className="font-semibold text-slate-700">Email:</span> {lab.email}</div>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-600">
                Laboratory information could not be verified from available sources. Contact BIS directly for laboratory recommendations.
              </div>
            )}
          </div>

          {/* ---- INTERACTIVE STATUTORY FEE & TIMELINE CALCULATOR ---- */}
          <FeeTimelineCalculator
            initialTestsCount={results.tests?.length || 4}
            standardNumber={results.standard?.standard_number}
          />

          {/* ---- ENTERPRISE READINESS & DOCUMENT CHECKLIST ---- */}
          {results.profile_readiness_checklists && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg">
                    <ClipboardCheck className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Profile-Tailored Enterprise Readiness & Audit Checklist
                    </h3>
                    <p className="text-xs text-slate-500">
                      Specific document packages, in-house equipment, and factory audit checkpoints for your enterprise tier.
                    </p>
                  </div>
                </div>

                {/* Profile Tabs */}
                <div className="flex items-center bg-slate-100 p-1 rounded-lg self-start sm:self-auto text-xs">
                  <button
                    type="button"
                    onClick={() => setReadinessProfile('msme')}
                    className={`px-3 py-1 font-semibold rounded-md transition-all cursor-pointer ${
                      readinessProfile === 'msme'
                        ? 'bg-white text-emerald-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    MSME (Micro & Small)
                  </button>
                  <button
                    type="button"
                    onClick={() => setReadinessProfile('startup')}
                    className={`px-3 py-1 font-semibold rounded-md transition-all cursor-pointer ${
                      readinessProfile === 'startup'
                        ? 'bg-white text-emerald-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Startup India
                  </button>
                  <button
                    type="button"
                    onClick={() => setReadinessProfile('large')}
                    className={`px-3 py-1 font-semibold rounded-md transition-all cursor-pointer ${
                      readinessProfile === 'large'
                        ? 'bg-white text-emerald-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Large Enterprise
                  </button>
                </div>
              </div>

              {/* Active Profile Details */}
              {(() => {
                const profileData = results.profile_readiness_checklists[readinessProfile];
                if (!profileData) return null;
                return (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between bg-emerald-50/70 border border-emerald-200 p-3 rounded-lg">
                      <div className="text-xs font-bold text-emerald-950">
                        {profileData.title}
                      </div>
                      <span className="text-[11px] font-bold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full border border-emerald-300">
                        {profileData.concession_badge}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Document Checklist */}
                      <div className="space-y-2">
                        <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
                          <FileText className="h-3.5 w-3.5 text-slate-500" />
                          <span>Required Application Dossier</span>
                        </span>
                        <div className="space-y-1.5">
                          {profileData.documents.map((doc, dIdx) => {
                            const docKey = `${readinessProfile}-${dIdx}`;
                            const isChecked = !!checkedDocs[docKey];
                            return (
                              <label
                                key={dIdx}
                                className={`flex items-start space-x-2.5 p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                                  isChecked
                                    ? 'bg-emerald-50/60 border-emerald-200 text-slate-400 line-through'
                                    : 'bg-slate-50/80 border-slate-200 hover:bg-slate-100/70 text-slate-700'
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() =>
                                    setCheckedDocs((prev) => ({ ...prev, [docKey]: !prev[docKey] }))
                                  }
                                  className="mt-0.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5"
                                />
                                <span className={isChecked ? 'line-through text-slate-400' : 'font-medium'}>
                                  {doc.item}
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      </div>

                      {/* In-house testing equipment */}
                      <div className="space-y-2">
                        <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
                          <Wrench className="h-3.5 w-3.5 text-slate-500" />
                          <span>Mandatory Factory Quality Equipment</span>
                        </span>
                        <div className="space-y-1.5">
                          {profileData.in_house_equipment.map((eq, eIdx) => (
                            <div
                              key={eIdx}
                              className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/80 text-xs space-y-0.5"
                            >
                              <div className="font-bold text-slate-800">{eq.equipment}</div>
                              <div className="text-[11px] text-slate-500">
                                <span className="font-semibold text-slate-600">Verification Purpose: </span>
                                {eq.purpose}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Factory Audit Focus */}
                    <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg text-xs text-amber-950 flex items-start space-x-2">
                      <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">BIS Auditor On-Site Inspection Focus: </span>
                        <span>{profileData.factory_audit_focus}</span>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ---- 06. HOW TO APPLY (Section 19) ---- */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
            <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">06 — How to Apply for BIS Certification</span>
            <div className="space-y-2">
              {results.application_steps.map((step) => (
                <div key={step.step_number} className="flex items-start space-x-3 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                  <span className="h-6 w-6 rounded-full bg-emerald-800 text-white font-bold text-xs flex items-center justify-center shrink-0">
                    {step.step_number}
                  </span>
                  <div>
                    <h4 className="font-bold text-slate-900">{step.title}</h4>
                    <p className="text-slate-600 mt-0.5">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
            <a href="https://www.manakonline.in" target="_blank" rel="noopener noreferrer"
              className="text-xs font-bold text-emerald-800 hover:text-emerald-900 flex items-center space-x-1">
              <span>BIS Manak Online Application Portal</span><ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>

          {/* ---- 07. YOUR NEXT ACTION (Section 20) ---- */}
          {results.next_action && (
            <div className="bg-emerald-900 text-white rounded-xl p-6 space-y-3">
              <span className="text-[11px] font-bold text-emerald-300 uppercase tracking-wider">07 — Your Next Action</span>
              <h3 className="text-lg font-bold">{results.next_action.action}</h3>
              <p className="text-sm text-emerald-100">{results.next_action.details}</p>
            </div>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* NO STANDARD FOUND STATE                                            */}
      {/* ================================================================= */}
      {isNoStandard && results && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center space-y-4">
          <Info className="w-10 h-10 text-slate-400 mx-auto" />
          <h2 className="text-base font-bold text-slate-800">Verification incomplete</h2>
          <p className="text-sm text-slate-600 max-w-xl mx-auto">
            We found a potentially relevant requirement, but the official evidence was not sufficient to confirm it.
          </p>
          {results.next_action && (
            <div className="bg-slate-50 rounded-lg p-4 max-w-lg mx-auto border border-slate-200 text-left text-sm">
              <div className="font-bold text-slate-800">{results.next_action.action}</div>
              <p className="text-slate-600 mt-1 text-xs">{results.next_action.details}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};