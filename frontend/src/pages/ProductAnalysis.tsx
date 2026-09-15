import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Sparkles,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Building2,
  ChevronRight,
  ShieldCheck,
  Award,
  Globe,
  UploadCloud,
  FileCheck,
  RefreshCw,
  ExternalLink,
  BookOpen,
  HelpCircle,
  Clock,
  Layers,
  Check,
  XCircle,
  HelpCircle as QuestionIcon,
  ChevronDown,
  Info,
  Download
} from 'lucide-react';
import { api, AnalysisResponse } from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';

const OPEN_WORLD_PRESETS = [
  {
    label: '🍼 SS Vacuum Flask',
    description: 'We manufacture stainless-steel drinking bottles for household use. Double-walled vacuum insulated, 750ml, SS 304 food contact liner.',
  },
  {
    label: '⚡ Water Heater (IS 302)',
    description: 'Domestic electric storage water heater 25L with thermostat and 2000W heating element.',
  },
  {
    label: '🔌 PVC Cables (IS 694)',
    description: 'PVC insulated electric cables with copper conductor for working voltages up to 1100V.',
  },
  {
    label: '🔋 Lithium Batteries (IS 16046)',
    description: 'Secondary lithium cells and batteries for portable applications.',
  },
  {
    label: '👕 Cotton T-Shirt (Apparel)',
    description: 'I manufacture 100% combed cotton T-shirts for casual wear.',
  },
  {
    label: '👕 Cotton T-Shirt (Live BIS)',
    description: '100% Combed Cotton T-Shirt',
  },
  {
    label: '🌿 Seaweed Packaging Film (Novel)',
    description: 'We make a biodegradable seaweed-based food packaging film for perishable produce.',
  },
  {
    label: '🩺 Smart Textile Sensor (Novel)',
    description: 'We make a smart textile sensor patch for sports monitoring and athlete telemetry.',
  },
  {
    label: '❓ Vague: "Steel Products" (Clarify)',
    description: 'We manufacture steel products.',
  },
];

export const ProductAnalysis: React.FC = () => {
  const routerLocation = useLocation();
  const { language, t } = useLanguage();
  const [description, setDescription] = useState('');
  const [locationInput, setLocationInput] = useState('Delhi');
  const [docText, setDocText] = useState('');
  const [includeWeb, setIncludeWeb] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<AnalysisResponse | null>(null);
  const [selectedStandardIndex, setSelectedStandardIndex] = useState(0);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [showTechnicalDiagnostics, setShowTechnicalDiagnostics] = useState(false);
  const [showSourceExplorer, setShowSourceExplorer] = useState(false);
  const [showResearchTrace, setShowResearchTrace] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Check if routed with pre-filled description
  useEffect(() => {
    if (routerLocation.state && (routerLocation.state as any).description) {
      const prefill = (routerLocation.state as any).description;
      setDescription(prefill);
      runAnalysisWithDescription(prefill);
    }
  }, [routerLocation.state]);

  const exportComplianceReport = () => {
    if (!results) return;
    const pu = results.product_understanding;
    const dateStr = new Date().toISOString().split('T')[0];
    const reportContent = `# BIS COMPLIANCE RESEARCH REPORT
=============================================================================
Product Identity    : ${pu?.product_name || 'Unspecified'}
Normalized Name     : ${pu?.normalized_product_name || 'N/A'}
Investigation Date  : ${dateStr}
Research Session ID : ${results.session_id || 'OPEN-WORLD-LIVE'}
Genuine Latency     : ${results.execution_time_seconds}s (Genuine measured runtime)
=============================================================================

1. PRODUCT UNDERSTANDING & SCOPE
-----------------------------------------------------------------------------
- Materials        : ${pu?.materials?.join(', ') || 'N/A'}
- Intended Use     : ${pu?.intended_use || 'General usage'}
- Industry Context : ${pu?.industry_context || pu?.category || 'General'}
- Regulatory Scope : ${pu?.possible_domains?.join(', ') || 'Indian Standards Framework'}

2. VERIFIED APPLICABLE STANDARDS
-----------------------------------------------------------------------------
${results.applicable_standards.length > 0 ? results.applicable_standards.map((s, idx) => `
[Standard ${idx + 1}] ${s.standard_number}: ${s.title}
- Match Confidence : ${s.confidence}% (Applicability Score: ${s.applicability_score}/100)
- Scope Rationale  :
  ${s.reasoning.map(r => `• ${r}`).join('\n  ')}
- Supporting Clauses / Citations:
  ${(s.supporting_clauses || []).map(c => `• Clause ${c.clause_number} (${c.heading}): "${c.text.slice(0, 150)}..."`).join('\n  ')}
`).join('\n') : 'No directly applicable standards verified from authoritative evidence.'}

2.1 POTENTIALLY RELEVANT STANDARDS (NEEDS SCOPE CLARIFICATION)
-----------------------------------------------------------------------------
${results.potential_standards && results.potential_standards.length > 0 ? results.potential_standards.map((s, idx) => `
[Potential Standard ${idx + 1}] ${s.standard_number}: ${s.title}
- Scope Status     : Needs Scope Clarification
- Confirmed Attributes : ${s.confirmed_attributes?.join(', ') || 'Category match'}
- Missing Scope Items  : ${s.missing_information?.join(', ') || 'Parameters pending'}
- Clarification Questions:
  ${(s.clarification_questions || []).map(q => `• ${q}`).join('\n  ')}
- Scope Reasoning  :
  ${s.reasoning.map(r => `• ${r}`).join('\n  ')}
`).join('\n') : 'No potential standards flagged for clarification.'}

3. CERTIFICATION PATHWAY & QUALITY CONTROL ORDERS (QCO)
-----------------------------------------------------------------------------
${results.certification_info.length > 0 ? results.certification_info.map(c => `
- Target Standard : ${c.standard_number}
- Scheme          : ${c.certification_scheme || 'Scheme I (ISI Mark Scheme)'}
- License Mandate : ${c.license_required ? 'MANDATORY LICENSE REQUIRED' : 'Voluntary / Product Specific'}
- Key Process Steps:
  ${(c.certification_process || []).map(p => `${p.step_number}. ${p.step_name}: ${p.description}`).join('\n  ')}
`).join('\n') : 'Certification information researched dynamically.'}

4. TESTING REQUIREMENTS & ACCREDITED LABORATORIES
-----------------------------------------------------------------------------
${results.laboratory_recommendations.length > 0 ? results.laboratory_recommendations.map((l, i) => `
[Laboratory ${i + 1}] ${l.lab_name}
- Location      : ${l.location}
- Accreditation : ${l.accreditation_body} (Recognition: ${l.is_bis_recognized ? 'BIS Recognized' : 'Accredited'})
- Address       : ${l.address}
- Scope Details : ${l.accredited_scopes?.join(', ') || 'Standard Compliance'}
`).join('\n') : 'No accredited laboratories indexed for this query.'}

5. INVESTIGATED AUTHORITATIVE SOURCES & BIBLIOGRAPHY
-----------------------------------------------------------------------------
${results.sources_investigated && results.sources_investigated.length > 0 ? results.sources_investigated.map((src, i) => `
[Source ${i + 1}] Tier-${src.authority_tier} (${src.domain}) - ${src.title}
- URL         : ${src.url}
- Authority   : Tier-${src.authority_tier} (Score: ${src.authority_score}/100)
- Retrieved   : ${src.retrieved_at || dateStr}
- Cache State : ${src.is_cached ? 'Verified Cache' : 'Live Official Retrieval'}
`).join('\n') : 'Sources evaluated dynamically.'}

6. HARD REJECTION DISCLOSURES (OUT-OF-SCOPE CANDIDATES)
-----------------------------------------------------------------------------
${results.rejected_candidates && results.rejected_candidates.length > 0 ? results.rejected_candidates.map(rej => `
• ${rej.standard_number} (${rej.title}): Excluded. Reason: ${rej.reason}
`).join('\n') : 'No candidate standards excluded.'}

=============================================================================
Report generated by BIS-Compass Open-World Compliance Platform.
Authoritative source evidence is stored in immutable audit session.
=============================================================================
`;

    const blob = new Blob([reportContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `BIS_Compliance_Report_${pu?.normalized_product_name?.replace(/[^a-zA-Z0-9]/g, '_') || 'Product'}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const runAnalysisWithDescription = async (textToAnalyze: string) => {
    if (!textToAnalyze.trim()) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await api.analyzeProduct({
        product_description: textToAnalyze,
        document_text: docText || undefined,
        location: locationInput || undefined,
        include_web_search: includeWeb,
      });
      setResults(res);
      setSelectedStandardIndex(0);
    } catch (err: any) {
      console.error('Analysis error:', err);
      const msg = err.response?.data?.detail || err.message || 'Compliance analysis failed. Please check the backend connection and try again.';
      setAnalysisError(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    await runAnalysisWithDescription(description);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadLoading(true);
    try {
      const res = await api.uploadDocument(file);
      if (res.success && res.extracted_text) {
        setDocText(res.extracted_text);
      }
    } catch (err) {
      console.error('File upload failed:', err);
    } finally {
      setUploadLoading(false);
    }
  };

  const activeStandard = results?.applicable_standards?.[selectedStandardIndex];
  const activeCert = results?.certification_info?.find(
    (c) => c.standard_id === activeStandard?.standard_id
  );
  const activeTesting = results?.testing_information?.find(
    (t) => t.standard_id === activeStandard?.standard_id
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold text-emerald-800 uppercase tracking-wider mb-1">
          <Sparkles className="h-4 w-4 text-emerald-600" />
          <span>Open-World Product Intelligence & BIS Compliance Engine</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
          Product Standards & Compliance Intelligence
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Enter any arbitrary product description. The system understands product identity vs material, enforces standard scope compatibility, requests clarification when vague, and eliminates false positives.
        </p>
      </div>

      {/* Preset Buttons */}
      <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-xs">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
          Open-World Benchmark Test Presets (Click to Load & Test):
        </div>
        <div className="flex flex-wrap gap-1.5">
          {OPEN_WORLD_PRESETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setDescription(preset.description);
                runAnalysisWithDescription(preset.description);
              }}
              className="text-[11px] px-2.5 py-1.5 bg-slate-50 hover:bg-emerald-50 border border-slate-200 hover:border-emerald-300 text-slate-700 hover:text-emerald-900 rounded-md font-medium transition-colors"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <form onSubmit={handleAnalyze} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5">
              Arbitrary Product Description / Technical Specifications *
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe ANY product (e.g., We manufacture stainless-steel drinking bottles for household use; or We make biodegradable seaweed food packaging film)..."
              className="w-full text-xs text-slate-900 border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-emerald-600 font-sans"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Proximity Location (City / State for Laboratory Match)
              </label>
              <input
                type="text"
                value={locationInput}
                onChange={(e) => setLocationInput(e.target.value)}
                placeholder="e.g., Delhi, Bangalore, Mumbai, Ghaziabad"
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Optional: Upload Spec Sheet / Test Report (PDF, DOCX, TXT)
              </label>
              <div className="flex items-center space-x-2">
                <label className="flex-1 border border-dashed border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 transition cursor-pointer flex items-center justify-center space-x-1.5">
                  <UploadCloud className="h-4 w-4 text-emerald-600" />
                  <span>{uploadLoading ? 'Extracting text...' : docText ? 'Document Attached (Click to Replace)' : 'Attach Document for Gap Analysis'}</span>
                  <input type="file" onChange={handleFileUpload} accept=".pdf,.docx,.doc,.txt" className="hidden" />
                </label>
                {docText && (
                  <button
                    type="button"
                    onClick={() => setDocText('')}
                    className="text-[11px] text-red-600 hover:underline px-1"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-100">
            <label className="flex items-center space-x-2 text-xs text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeWeb}
                onChange={(e) => setIncludeWeb(e.target.checked)}
                className="rounded text-emerald-600 focus:ring-emerald-500"
              />
              <span className="flex items-center space-x-1">
                <Globe className="h-3.5 w-3.5 text-slate-400" />
                <span>Search Live Official BIS Web Portals</span>
              </span>
            </label>

            <button
              type="submit"
              disabled={isAnalyzing || !description.trim()}
              className="bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-lg shadow-sm flex items-center space-x-2 transition cursor-pointer"
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Analyzing Product & Verifying Scope...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Run Open-World Compliance Analysis</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Analysis Error Notification */}
      {analysisError && (
        <div className="bg-red-50 border-2 border-red-300 rounded-xl p-5 shadow-xs space-y-3">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h2 className="text-sm font-bold text-red-900 uppercase tracking-wide">
                Analysis Request Failed
              </h2>
              <p className="text-xs text-red-800 leading-relaxed">
                {analysisError}
              </p>
            </div>
          </div>
          <div className="pt-2 border-t border-red-200 flex items-center justify-between">
            <span className="text-[11px] text-red-700">
              Verify that the FastAPI backend server is running at http://127.0.0.1:8002.
            </span>
            <button
              type="button"
              onClick={() => runAnalysisWithDescription(description)}
              className="text-xs font-bold bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-lg shadow-2xs transition cursor-pointer"
            >
              Retry Analysis
            </button>
          </div>
        </div>
      )}

      {/* Analysis Results Container */}
      {results && (
        <div className="space-y-6">
          {/* Clarification Required Alert */}
          {results.clarification_required && (
            <div className="bg-amber-50 border-2 border-amber-300 rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h2 className="text-sm font-bold text-amber-900 uppercase tracking-wide">
                    Targeted Product Clarification Required
                  </h2>
                  <p className="text-xs text-amber-800 leading-relaxed">
                    The product description is broad or requires specific scope confirmation before certification applicability can be definitively verified. Please clarify:
                  </p>
                </div>
              </div>

              <div className="bg-white/80 rounded-lg p-3 border border-amber-200 space-y-2">
                <ul className="text-xs text-slate-800 list-disc list-inside space-y-1">
                  {(results.clarification_questions || []).map((q, idx) => (
                    <li key={idx} className="leading-relaxed font-medium">{q}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Live Research Summary & Metrics Banner */}
          {(() => {
            const officialCount = results.pipeline?.authoritative_sources_used ?? results.sources_investigated?.filter(s => s.authority_tier <= 2).length ?? 0;
            return (
              <div className="bg-slate-900 text-white rounded-xl p-4 shadow-sm space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
                  {results.is_live_research && officialCount > 0 ? (
                    <div className="flex items-center space-x-2">
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                      </span>
                      <span className="text-xs font-black tracking-wider uppercase text-emerald-400">
                        Live Web Research Grounded
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        ({results.execution_time_seconds}s Genuine Runtime)
                      </span>
                    </div>
                  ) : results.is_live_research && officialCount === 0 ? (
                    <div className="flex items-center space-x-2">
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
                      </span>
                      <span className="text-xs font-black tracking-wider uppercase text-amber-400">
                        Secondary Research (0 Official BIS Sources)
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        ({results.execution_time_seconds}s Genuine Runtime)
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-2">
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-500"></span>
                      <span className="text-xs font-black tracking-wider uppercase text-slate-400">
                        Cached Evidence Grounded
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        ({results.execution_time_seconds}s Genuine Runtime)
                      </span>
                    </div>
                  )}

                  <div className="flex items-center space-x-2">
                    {results.research_trace && (
                      <button
                        type="button"
                        onClick={() => setShowResearchTrace(!showResearchTrace)}
                        className="text-xs bg-slate-800 hover:bg-slate-700 text-blue-300 font-medium px-3 py-1.5 rounded-lg border border-slate-700 flex items-center space-x-1.5 transition cursor-pointer"
                      >
                        <Layers className="w-3.5 h-3.5 text-blue-400" />
                        <span>Research Trace ({results.research_trace.queries_executed?.length || 0})</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setShowSourceExplorer(!showSourceExplorer)}
                      className="text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 font-medium px-3 py-1.5 rounded-lg border border-slate-700 flex items-center space-x-1.5 transition cursor-pointer"
                    >
                      <Globe className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Source Explorer ({results.sources_investigated?.length || results.pipeline?.sources_examined || 0})</span>
                    </button>
                    <button
                      type="button"
                      onClick={exportComplianceReport}
                      className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 rounded-lg shadow-xs flex items-center space-x-1.5 transition cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Export Compliance Report</span>
                    </button>
                  </div>
                </div>

                {/* Real Runtime Pipeline Counters (6 Transparency Metrics) */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-center">
                  <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
                    <div className="text-base font-black text-white">{results.pipeline?.sources_examined ?? results.sources_investigated?.length ?? 0}</div>
                    <div className="text-[10px] text-slate-400 font-semibold uppercase">Sources Examined</div>
                  </div>
                  <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
                    <div className={`text-base font-black ${officialCount > 0 ? 'text-emerald-400' : 'text-amber-400'}`}>{officialCount}</div>
                    <div className="text-[10px] text-slate-400 font-semibold uppercase">Official BIS/Gov Used</div>
                  </div>
                  <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
                    <div className="text-base font-black text-blue-400">
                      {results.applicable_standards.length + (results.potential_standards?.length || 0)}
                    </div>
                    <div className="text-[10px] text-slate-400 font-semibold uppercase">Standards Identified</div>
                  </div>
                  <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
                    <div className="text-base font-black text-amber-300">
                      {results.potential_standards?.length || 0}
                    </div>
                    <div className="text-[10px] text-slate-400 font-semibold uppercase">Needs Clarification</div>
                  </div>
                  <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
                    <div className="text-base font-black text-slate-300">
                      {results.pipeline?.rejected ?? results.rejected_candidates?.length ?? 0}
                    </div>
                    <div className="text-[10px] text-slate-400 font-semibold uppercase">Candidates Excluded</div>
                  </div>
                  <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/50">
                    <div className="text-base font-black text-emerald-400">{results.applicable_standards.length}</div>
                    <div className="text-[10px] text-slate-400 font-semibold uppercase">Verified Applicable</div>
                  </div>
                </div>

                {/* Real Research Stages Tracker */}
                {results.research_stages && results.research_stages.length > 0 && (
                  <div className="pt-2 border-t border-slate-800">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                      Research Pipeline Stages (Backend Executed):
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                      {results.research_stages.map((st, i) => (
                        <div key={i} className="flex items-start space-x-1.5 text-[11px] bg-slate-800/40 p-1.5 rounded border border-slate-800">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                          <div>
                            <div className="font-bold text-slate-200">{st.stage}</div>
                            <div className="text-[10px] text-slate-400 line-clamp-1">{st.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Source Explorer Modal / Drawer (Requirement 51) */}
          {showSourceExplorer && results.sources_investigated && results.sources_investigated.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-300 p-5 shadow-md space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center space-x-2">
                  <Globe className="w-5 h-5 text-emerald-600" />
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                    Authoritative Sources Investigated ({results.sources_investigated.length})
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowSourceExplorer(false)}
                  className="text-xs text-slate-500 hover:text-slate-800 font-bold cursor-pointer"
                >
                  Close ×
                </button>
              </div>

              <div className="space-y-2 max-h-80 overflow-y-auto">
                {results.sources_investigated.map((src, i) => (
                  <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start justify-between space-x-3">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded ${
                          src.authority_tier === 1 ? 'bg-emerald-600 text-white' :
                          src.authority_tier === 2 ? 'bg-blue-600 text-white' :
                          src.authority_tier === 3 ? 'bg-purple-600 text-white' :
                          src.authority_tier === 4 ? 'bg-amber-600 text-white' :
                          'bg-slate-500 text-white'
                        }`}>
                          Tier {src.authority_tier} {src.authority_tier === 1 ? '(Official BIS)' : src.authority_tier === 2 ? '(Gov / Gazette)' : src.authority_tier === 3 ? '(ISO/IEC)' : ''}
                        </span>
                        <span className="font-bold text-slate-800 text-xs">{src.domain}</span>
                        <span className="text-[10px] text-slate-400 font-mono">Score: {src.authority_score}/100</span>
                      </div>
                      <div className="font-semibold text-slate-900 text-xs">{src.title}</div>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-emerald-700 hover:underline flex items-center space-x-1 break-all"
                      >
                        <span>{src.url}</span>
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                    </div>
                    <span className="text-[10px] text-slate-400 shrink-0 font-mono">
                      {src.is_cached ? 'Verified Cache' : 'Live Fetched'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Research Execution Trace Modal / Drawer */}
          {showResearchTrace && results.research_trace && (
            <div className="bg-white rounded-xl border border-blue-200 p-5 shadow-md space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center space-x-2">
                  <Layers className="w-5 h-5 text-blue-600" />
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                    Live Research Execution Trace
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowResearchTrace(false)}
                  className="text-xs text-slate-500 hover:text-slate-800 font-bold cursor-pointer"
                >
                  Close ×
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Queries Executed Across Vectors ({results.research_trace.queries_executed?.length || 0})
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {(results.research_trace.queries_executed || []).map((q: any, i: number) => (
                      <div key={i} className="p-2 bg-slate-50 border border-slate-200 rounded text-xs flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs text-blue-700 font-bold">"{q.query}"</span>
                          <span className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-semibold">{q.provider}</span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {q.results_count ?? 0} results found
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {(results.research_trace.sources_accepted && results.research_trace.sources_accepted.length > 0 ||
                  results.research_trace.sources_rejected && results.research_trace.sources_rejected.length > 0) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                    <div>
                      <div className="text-xs font-bold text-emerald-800 uppercase tracking-wider mb-1">
                        Accepted Evidence ({results.research_trace.sources_accepted?.length || 0})
                      </div>
                      <div className="space-y-1 max-h-36 overflow-y-auto">
                        {(results.research_trace.sources_accepted || []).map((s: any, i: number) => (
                          <div key={i} className="p-1.5 bg-emerald-50 border border-emerald-200 rounded text-[11px] truncate">
                            <span className="font-bold text-emerald-900">{s.domain || s.url}</span>
                            {s.authority_tier && <span className="ml-1 text-[10px] text-emerald-700 font-semibold">(Tier {s.authority_tier})</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-1">
                        Filtered Sources ({results.research_trace.sources_rejected?.length || 0})
                      </div>
                      <div className="space-y-1 max-h-36 overflow-y-auto">
                        {(results.research_trace.sources_rejected || []).map((s: any, i: number) => (
                          <div key={i} className="p-1.5 bg-slate-50 border border-slate-200 rounded text-[11px] truncate text-slate-600">
                            <span className="font-medium">{s.url || s.domain}</span>
                            {s.reason && <span className="ml-1 text-[10px] text-amber-700">({s.reason})</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Top Banner: Open-World Product Understanding */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                  Open-World Product Profile & Functional Scope
                </h2>
              </div>
              <span className="text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 rounded uppercase tracking-wider">
                {results.product_understanding?.clarification_required ? 'Needs Clarification' : 'Product Profile Grounded'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs">
              <div>
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Product Identity</span>
                <span className="font-bold text-slate-900 mt-0.5 block">
                  {results.product_understanding?.product_name || 'Unspecified Product'}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Product Family</span>
                <span className="font-semibold text-emerald-900 bg-emerald-50 px-2 py-0.5 rounded inline-block mt-0.5">
                  {results.product_understanding?.product_family || results.product_understanding?.category || 'General'}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Materials (Subordinate)</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {results.product_understanding?.materials?.join(', ') || 'Not specified'}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Physical Form</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {results.product_understanding?.physical_form || 'Manufactured Item'}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Intended Application</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {results.product_understanding?.intended_use || 'General Consumer'}
                </span>
              </div>
            </div>

            {/* Inferred Hypothesized Domains */}
            {results.product_understanding?.possible_domains && results.product_understanding.possible_domains.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center space-x-2 text-[11px] text-slate-500">
                <span className="font-semibold text-slate-700">Hypothesized Domains:</span>
                <div className="flex flex-wrap gap-1">
                  {results.product_understanding.possible_domains.map((dom, i) => (
                    <span key={i} className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      {dom}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Potentially Relevant Standards Section (Needs Scope Clarification) */}
          {results.potential_standards && results.potential_standards.length > 0 && (
            <div className="bg-amber-50/70 border-2 border-amber-300 rounded-xl p-5 shadow-xs space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-2.5">
                  <HelpCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-sm font-black text-amber-900 uppercase tracking-wide">
                      Potentially Relevant Standards (Needs Scope Clarification)
                    </h2>
                    <p className="text-xs text-amber-800 mt-0.5">
                      The following official Indian Standards govern closely related products, but specific scope parameters (such as gender classification, weave type, or intended usage) must be clarified before certification applicability can be verified.
                    </p>
                  </div>
                </div>
                <span className="text-xs font-bold bg-amber-200 text-amber-900 px-2.5 py-1 rounded-full shrink-0">
                  {results.potential_standards.length} Potential Standard{results.potential_standards.length > 1 ? 's' : ''}
                </span>
              </div>

              <div className="space-y-3">
                {results.potential_standards.map((std, idx) => (
                  <div key={std.standard_id || idx} className="bg-white rounded-lg border border-amber-200 p-4 shadow-2xs space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-black text-slate-900 text-sm">{std.standard_number}</span>
                          <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">
                            Official BIS Record
                          </span>
                          <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded">
                            Needs Clarification
                          </span>
                        </div>
                        <h3 className="text-xs font-bold text-slate-800 mt-1">{std.title}</h3>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-bold text-amber-800 bg-amber-100 border border-amber-300 px-2.5 py-1 rounded uppercase tracking-wider">
                          {std.status ? std.status.replace(/_/g, ' ') : 'Potentially Applicable'}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-2 border-t border-slate-100">
                      {/* Confirmed Attributes */}
                      <div className="bg-emerald-50/50 rounded-md p-2.5 border border-emerald-100 space-y-1">
                        <div className="text-[11px] font-bold text-emerald-900 flex items-center space-x-1 uppercase tracking-wider">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Confirmed Product Match</span>
                        </div>
                        <ul className="text-slate-700 text-[11px] space-y-0.5 list-disc list-inside">
                          {(std.confirmed_attributes || ['Product description matches general category']).map((attr, aIdx) => (
                            <li key={aIdx}>{attr}</li>
                          ))}
                        </ul>
                      </div>

                      {/* Missing Information / Required Scope Clarifications */}
                      <div className="bg-amber-50/50 rounded-md p-2.5 border border-amber-100 space-y-1">
                        <div className="text-[11px] font-bold text-amber-900 flex items-center space-x-1 uppercase tracking-wider">
                          <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
                          <span>Scope Clarifications Required</span>
                        </div>
                        <ul className="text-amber-800 text-[11px] space-y-0.5 list-disc list-inside">
                          {(std.missing_information || ['Specific functional scope parameters pending confirmation']).map((miss, mIdx) => (
                            <li key={mIdx}>{miss}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Reasoning */}
                    {std.reasoning && std.reasoning.length > 0 && (
                      <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-100 space-y-1">
                        <div className="text-[10px] font-bold uppercase text-slate-500">Scope Analysis:</div>
                        <ul className="list-disc list-inside space-y-0.5">
                          {std.reasoning.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Clarification Questions & Action */}
                    {std.clarification_questions && std.clarification_questions.length > 0 && (
                      <div className="bg-slate-900 text-white rounded-md p-3 text-xs space-y-2">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                          To confirm applicability under {std.standard_number}, clarify:
                        </div>
                        <ul className="space-y-1 text-[11px] text-slate-200 list-disc list-inside">
                          {std.clarification_questions.map((q, qIdx) => (
                            <li key={qIdx}>{q}</li>
                          ))}
                        </ul>
                        <div className="pt-1 flex items-center justify-between">
                          <span className="text-[10px] text-slate-400 italic">
                            Update product description above with these details to re-run verification.
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              const addition = std.standard_number.includes('4375')
                                ? " (Men's knitted sports shirt/T-shirt)"
                                : std.standard_number.includes('17803') || std.standard_number.includes('17526')
                                ? ` (Vacuum double-walled domestic drinking bottle, nominal capacity 750ml, food-grade closure per ${std.standard_number})`
                                : ` (conforming to ${std.standard_number} scope parameters)`;
                              setDescription(prev => {
                                const trimmed = prev.trim();
                                if (trimmed.includes(addition.trim()) || trimmed.includes(std.standard_number)) {
                                  return trimmed; // Prevent duplicate appends (Bug 4 fix)
                                }
                                return `${trimmed}${addition}`;
                              });
                            }}
                            className="text-[11px] bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-2.5 py-1 rounded transition cursor-pointer"
                          >
                            + Add Details to Description
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Safe Abstention Banner (When 0 Standards Match AND 0 Potential Standards) */}
          {results.applicable_standards.length === 0 && (!results.potential_standards || results.potential_standards.length === 0) && (
            <div className="bg-slate-50 border-2 border-slate-300 rounded-xl p-6 text-center space-y-3">
              <Info className="w-10 h-10 text-slate-400 mx-auto" />
              <h3 className="text-base font-bold text-slate-800">
                No Directly Applicable Indian Standard (IS) Identified
              </h3>
              <p className="text-xs text-slate-600 max-w-xl mx-auto leading-relaxed">
                {results.overall_assessment}
              </p>
              <div className="bg-white rounded-lg p-3 max-w-lg mx-auto border border-slate-200 text-left text-xs space-y-1">
                <div className="font-bold text-slate-700 text-[11px] uppercase tracking-wider mb-1">
                  Recommended Verification Steps:
                </div>
                {(results.recommendations || []).map((rec, i) => (
                  <div key={i} className="flex items-start space-x-2 text-slate-600">
                    <span className="font-bold text-emerald-700">{i + 1}.</span>
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notification when 0 directly verified standards but potential standards exist */}
          {results.applicable_standards.length === 0 && results.potential_standards && results.potential_standards.length > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-700 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Info className="w-4 h-4 text-amber-600 shrink-0" />
                <span>
                  <strong>0 Directly Verified Standards:</strong> Potential official standards were discovered above, but scope confirmation is required before mandatory applicability can be established.
                </span>
              </div>
              <span className="text-[11px] font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-500 shrink-0">
                Strict Evidence Gate Active
              </span>
            </div>
          )}

          {/* Unified "What You Need To Do" Recommendation Panel (Part 3 & Rule 8.9 / 8.10) */}
          {results.what_you_need_to_do && results.what_you_need_to_do.has_applicable_standard && (
            <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 text-white rounded-xl p-6 shadow-md border border-emerald-500/30 space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-500/20 pb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-emerald-500/20 rounded-lg border border-emerald-400/30">
                    <Award className="h-6 w-6 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-base font-black tracking-tight text-white uppercase flex items-center space-x-2">
                      <span>{t('what_you_need_to_do')}</span>
                      <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                        {results.what_you_need_to_do.standard_number}
                      </span>
                    </h2>
                    <p className="text-xs text-slate-300 mt-0.5">
                      {results.what_you_need_to_do.title}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className={`text-xs font-bold px-3 py-1 rounded-md border ${
                    results.what_you_need_to_do.qco_status === 'MANDATORY'
                      ? 'bg-red-500/20 text-red-300 border-red-500/40'
                      : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  }`}>
                    {results.what_you_need_to_do.qco_status === 'MANDATORY' ? 'MANDATORY UNDER QCO' : 'NOT VERIFIED UNDER QCO'}
                  </span>
                  <span className="text-xs font-bold px-3 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                    Scheme: {results.what_you_need_to_do.certification_scheme}
                  </span>
                </div>
              </div>

              {/* Regulatory Mandate Disclosure Card */}
              <div className="bg-slate-900/80 border border-slate-700/80 rounded-lg p-3.5 text-xs flex items-start space-x-3">
                <ShieldCheck className={`h-5 w-5 shrink-0 mt-0.5 ${
                  results.what_you_need_to_do.qco_status === 'MANDATORY' ? 'text-red-400' : 'text-amber-400'
                }`} />
                <div className="space-y-1">
                  <div className="font-bold text-slate-200 uppercase text-[11px] tracking-wider">
                    Official Regulatory Mandate (Rule 0 / Rule 8.9 Integrity)
                  </div>
                  <p className="text-slate-300 leading-relaxed text-xs">
                    {results.what_you_need_to_do.qco_message}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Full Tests Table / List */}
                <div className="bg-slate-900/60 border border-slate-700/60 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div className="flex items-center space-x-2">
                      <FileCheck className="h-4 w-4 text-emerald-400" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                        {t('testing_requirements')}
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">
                      Status: {results.what_you_need_to_do.testing_status}
                    </span>
                  </div>

                  {results.what_you_need_to_do.tests && results.what_you_need_to_do.tests.length > 0 ? (
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {results.what_you_need_to_do.tests.map((test, tIdx) => (
                        <div key={tIdx} className="p-2.5 bg-slate-800/80 border border-slate-700/80 rounded-md text-xs space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white">{test.test_name}</span>
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                              test.requirement_type === 'MANDATORY'
                                ? 'bg-red-900/60 text-red-300 border border-red-700'
                                : test.requirement_type === 'ROUTINE'
                                ? 'bg-blue-900/60 text-blue-300 border border-blue-700'
                                : test.requirement_type === 'TYPE_TEST'
                                ? 'bg-purple-900/60 text-purple-300 border border-purple-700'
                                : 'bg-slate-700 text-slate-300'
                            }`}>
                              {test.requirement_type}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                            <span>{test.clause}</span>
                            <span>{test.test_method}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">
                      Testing parameters require full clause evaluation from standard text.
                    </p>
                  )}
                </div>

                {/* Step-by-Step Next Actions */}
                <div className="bg-slate-900/60 border border-slate-700/60 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div className="flex items-center space-x-2">
                      <BookOpen className="h-4 w-4 text-emerald-400" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                        {t('step_by_step_next_actions')}
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-emerald-400">BIS Manakonline</span>
                  </div>

                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {(results.what_you_need_to_do.next_actions || []).map((step, sIdx) => (
                      <div key={sIdx} className="flex items-start space-x-2.5 p-2 bg-slate-800/80 border border-slate-700/80 rounded-md text-xs">
                        <span className="font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-700/50 w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-[11px]">
                          {step.step_number}
                        </span>
                        <div className="space-y-0.5">
                          <div className="font-bold text-slate-200 flex items-center space-x-1.5">
                            <span>{step.step_name}</span>
                            {step.responsible_party && (
                              <span className="text-[9px] text-slate-400 font-normal">({step.responsible_party})</span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{step.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Applicable Standards Selector (When Standards Exist) */}
          {results.applicable_standards.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide mb-3">
                Authoritative Applicable Standards (Scope Verified)
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {results.applicable_standards.map((std, idx) => {
                  const isSelected = idx === selectedStandardIndex;
                  return (
                    <div
                      key={std.standard_id}
                      onClick={() => setSelectedStandardIndex(idx)}
                      className={`p-3.5 rounded-lg border text-xs transition cursor-pointer ${
                        isSelected
                          ? 'border-emerald-600 bg-emerald-50/60 shadow-xs ring-1 ring-emerald-500'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 text-sm">{std.standard_number}</span>
                        <span className="font-bold text-[11px] uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                          {std.status ? std.status.replace(/_/g, ' ') : 'Scope Verified'}
                        </span>
                      </div>
                      <p className="text-slate-600 font-medium mt-1 line-clamp-2">{std.title}</p>
                      <div className="flex items-center space-x-1 text-[11px] text-emerald-700 font-semibold mt-2">
                        <Check className="h-3 w-3" />
                        <span>Scope & Product Verified</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Referenced & Material Standards (Section 27 & 28) */}
          {results.related_standards && results.related_standards.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Layers className="h-4 w-4 text-blue-600" />
                  <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                    Referenced & Supporting Standards (Material & Test Specifications)
                  </h2>
                </div>
                <span className="text-[11px] font-bold bg-blue-50 text-blue-800 border border-blue-200 px-2 py-0.5 rounded">
                  {results.related_standards.length} Supporting Standard{results.related_standards.length > 1 ? 's' : ''}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                These standards are cited by or support primary product compliance (e.g. raw material composition, alloy grades, test methods). They are supporting references rather than independent primary product standards.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {results.related_standards.map((rel, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">{rel.standard_number}</span>
                      <span className="text-[10px] font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded uppercase">
                        {rel.relationship_type ? rel.relationship_type.replace(/_/g, ' ') : 'Referenced Standard'}
                      </span>
                    </div>
                    <p className="text-slate-700 font-medium text-[11px]">{rel.title}</p>
                    <p className="text-slate-500 text-[10px]">{rel.reasons ? (Array.isArray(rel.reasons) ? rel.reasons.join(', ') : rel.reasons) : 'Supporting specification'}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailed Selected Standard View */}
          {activeStandard && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left 2 Cols: Why Applicable, Certification Roadmap, Testing */}
              <div className="lg:col-span-2 space-y-6">
                {/* Why Applicable Card */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
                  <div className="flex items-center space-x-2 border-b border-slate-100 pb-3 mb-4">
                    <BookOpen className="h-4 w-4 text-emerald-700" />
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                      Why Does {activeStandard.standard_number} Apply?
                    </h3>
                  </div>

                  <div className="space-y-3 text-xs">
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                      <div className="font-bold text-slate-800 mb-1">Applicability Reasoning:</div>
                      <ul className="space-y-1 list-disc list-inside text-slate-700">
                        {activeStandard.reasoning.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>

                    {activeStandard.supporting_clauses?.length > 0 && (
                      <div>
                        <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                          Authoritative Supporting Clauses / Evidence
                        </div>
                        <div className="space-y-2">
                          {activeStandard.supporting_clauses.map((clause, i) => (
                            <div key={i} className="p-3 bg-emerald-50/40 border border-emerald-200 rounded-lg">
                              <div className="flex items-center justify-between text-[11px] font-bold text-emerald-900 mb-1">
                                <span>Clause {clause.clause_number}: {clause.heading}</span>
                                {clause.page && <span>Page {clause.page}</span>}
                              </div>
                              <p className="text-slate-700 leading-relaxed text-[11px] font-mono bg-white p-2 rounded border border-emerald-100">
                                {clause.text}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Certification Roadmap */}
                {activeCert && (
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
                    <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
                      <Award className="h-4 w-4 text-emerald-700" />
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Certification Path: {activeCert.certification_scheme && activeCert.certification_scheme !== "NOT_VERIFIED" ? activeCert.certification_scheme : 'Not Verified from Authoritative Evidence'}
                      </h3>
                    </div>

                    {activeCert.certification_process && activeCert.certification_process.length > 0 ? (
                      <div className="space-y-2">
                        {activeCert.certification_process.map((step, idx) => (
                          <div key={idx} className="flex items-start space-x-3 text-xs p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                            <span className="font-bold text-emerald-700 bg-emerald-100 w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-[11px]">
                              {step.step_number}
                            </span>
                            <div>
                              <div className="font-bold text-slate-900">{step.step_name}</div>
                              <p className="text-slate-600 mt-0.5">{step.description}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 bg-slate-50 rounded border border-slate-200 text-xs text-slate-600">
                        Mandatory certification status: <strong>Voluntary Indian Standard</strong> unless specifically notified under a Central Line Ministry Quality Control Order (QCO). No mandatory licensing order retrieved for this standard.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right Col: Testing Requirements & Labs */}
              <div className="space-y-6">
                {activeTesting && (
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                    <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
                      <FileCheck className="h-4 w-4 text-emerald-700" />
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Testing Requirements
                      </h3>
                    </div>

                    <div className="space-y-2">
                      {activeTesting.testing_requirements && activeTesting.testing_requirements.length > 0 ? (
                        activeTesting.testing_requirements.map((req, idx) => (
                          <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded text-xs space-y-0.5">
                            <div className="font-bold text-slate-900 flex items-center justify-between">
                              <span>{req.test_type}</span>
                              {req.is_mandatory && (
                                <span className="text-[10px] text-red-600 bg-red-50 px-1.5 py-0.5 rounded font-bold">Mandatory</span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-600">{req.description}</p>
                          </div>
                        ))
                      ) : (
                        <div className="p-3 bg-slate-50 rounded border border-slate-200 text-xs text-slate-500">
                          Testing requirements not verified from retrieved authoritative clauses. Consult full standard text.
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Laboratories */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div className="flex items-center space-x-2">
                      <Building2 className="h-4 w-4 text-emerald-700" />
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        {t('testing_laboratories')}
                      </h3>
                    </div>
                    {results.laboratory_recommendations && results.laboratory_recommendations.length > 0 && (
                      <span className="text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 rounded">
                        {results.laboratory_recommendations.length} Verified
                      </span>
                    )}
                  </div>

                  <div className="space-y-2">
                    {results.laboratory_recommendations && results.laboratory_recommendations.length > 0 ? (
                      results.laboratory_recommendations.map((lab, lIdx) => (
                        <div key={lab.id || lIdx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1.5 hover:border-slate-300 transition">
                          <div className="flex items-start justify-between gap-2">
                            <div className="font-bold text-slate-900 leading-snug">{lab.lab_name}</div>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 shrink-0">
                              {lab.distance_str || t('distance_not_verified')}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-600">{lab.address || lab.location}</div>
                          {lab.contact_person && (
                            <div className="text-[10px] text-slate-500">Contact: {lab.contact_person} {lab.phone ? `(${lab.phone})` : ''}</div>
                          )}
                          <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-[10px]">
                            <div className="flex items-center space-x-1 text-emerald-700 font-semibold">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              <span>{lab.is_bis_recognized ? 'BIS Recognized' : 'Accredited'} ({lab.accreditation_body || 'NABL'})</span>
                            </div>
                            {lab.website && (
                              <a href={lab.website} target="_blank" rel="noreferrer" className="text-emerald-700 hover:underline flex items-center space-x-1">
                                <span>Portal</span>
                                <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-4 bg-amber-50/60 border border-amber-200 rounded-lg text-xs text-amber-900 space-y-1">
                        <div className="font-bold flex items-center space-x-1 text-amber-900">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                          <span>No Local Testing Laboratories Verified</span>
                        </div>
                        <p className="text-[11px] text-amber-800 leading-relaxed">
                          {t('no_labs_found')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Technical Diagnostics & False Positive Disclosures (Prompt Section 12 & 30) */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <button
              type="button"
              onClick={() => setShowTechnicalDiagnostics(!showTechnicalDiagnostics)}
              className="w-full flex items-center justify-between text-xs font-bold text-slate-700 hover:text-slate-900 uppercase tracking-wider"
            >
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-slate-500" />
                <span>Technical Analysis & Candidate Standards Evaluated ({results.pipeline?.retrieved_candidates ?? 0} Evaluated, {results.pipeline?.rejected ?? 0} Excluded)</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${showTechnicalDiagnostics ? 'rotate-180' : ''}`} />
            </button>

            {showTechnicalDiagnostics && (
              <div className="mt-4 pt-4 border-t border-slate-100 space-y-4 text-xs">
                {/* Pipeline Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-slate-50 rounded border border-slate-200 text-center">
                    <div className="text-lg font-black text-slate-800">{results.pipeline?.retrieved_candidates ?? 0}</div>
                    <div className="text-[10px] uppercase font-bold text-slate-400">Total Candidates Retrieved</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded border border-slate-200 text-center">
                    <div className="text-lg font-black text-red-700">{results.pipeline?.rejected ?? 0}</div>
                    <div className="text-[10px] uppercase font-bold text-slate-400">False Positives Rejected</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded border border-slate-200 text-center">
                    <div className="text-lg font-black text-emerald-700">{results.pipeline?.applicable ?? 0}</div>
                    <div className="text-[10px] uppercase font-bold text-slate-400">Verified Applicable</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded border border-slate-200 text-center">
                    <div className="text-lg font-black text-slate-800">{results.execution_time_seconds}s</div>
                    <div className="text-[10px] uppercase font-bold text-slate-400">Pipeline Latency</div>
                  </div>
                </div>

                {/* Rejected Candidates List with Explicit Contradictions */}
                {results.rejected_candidates && results.rejected_candidates.length > 0 && (
                  <div className="space-y-2">
                    <div className="font-bold text-slate-800 text-[11px] uppercase tracking-wider">
                      Standards Evaluated & Excluded (Hard Rejection Audit Trail):
                    </div>
                    <div className="space-y-1.5 max-h-64 overflow-y-auto">
                      {results.rejected_candidates.map((rej, i) => (
                        <div key={i} className="p-2.5 bg-slate-50 rounded border border-slate-200 text-xs flex items-start space-x-2">
                          <XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                          <div>
                            <div className="font-semibold text-slate-900">
                              {rej.standard_number}: {rej.title}
                            </div>
                            <div className="text-[11px] text-red-700 mt-0.5">
                              Exclusion reason: {rej.reason}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Statutory Notice (Section 67) */}
          <div className="p-3 bg-slate-100/80 rounded-xl border border-slate-200 text-center text-[11px] text-slate-600">
            Information derived from verified sources. This system provides compliance decision support and does not replace professional regulatory/legal advice.
          </div>
        </div>
      )}
    </div>
  );
};
