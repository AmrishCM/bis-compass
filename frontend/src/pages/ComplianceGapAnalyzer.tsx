import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FileCheck,
  UploadCloud,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Info,
  ChevronDown
} from 'lucide-react';
import { api, ComplianceGapData } from '../services/api';

const SAMPLE_SPECS = {
  ss_bottle: {
    title: "Stainless Steel Vacuum Bottle - Specification Spec-2026",
    standard_number: "IS 17526:2021",
    standard_id: 1,
    text: `TECHNICAL SPECIFICATION: Domestic Stainless Steel Vacuum Insulated Flask
Product: Insulated Double-Walled Travel Bottle
Capacity: 750 ml
Material Composition:
- Inner Flask: SS 304 Grade Stainless Steel (Food Contact Surface)
- Outer Casing: SS 201 Stainless Steel with powder coat
- Stopper & Lid: Polypropylene (BPA Free) with Food Grade Silicone Gasket
Thermal Performance:
- Hot Retention: Water filled at 95°C maintains >60°C after 6 hours in 20°C ambient.
- Cold Retention: Chilled water at 4°C maintains <10°C after 12 hours.
Manufacturing Process:
- Deep drawn stainless steel body, laser welded bottom, high-vacuum evacuation sealed with getter.
Marking details:
- Embossed on base: Brand Name, 750ml, Made in India.
Missing details from documentation:
- No NABL heavy metal migration test report for lead and cadmium attached.
- No impact drop resistance test record attached.
- Standard IS 17526:2021 and ISI Certification Mark license number not yet engraved on carton.`
  },
  water_heater: {
    title: "Electric Storage Water Heater - Technical Data Sheet",
    standard_number: "IS 302-2-15:2009",
    standard_id: 2,
    text: `TECHNICAL SPECIFICATION: Electric Storage Water Heater (Geyser)
Model: AquaSafe-25L Domestic
Rated Voltage: 230V AC, 50Hz, Single Phase
Rated Power Input: 2000 Watts
Rated Storage Capacity: 25 Liters
Rated Pressure: 0.8 MPa (8 Bar) suitable for high-rise buildings
Safety Devices:
- Automatic Stem Thermostat (preset at 75°C)
- Thermal Cut-out with manual reset (trips at 90°C)
- Multifunctional Safety Valve (Pressure relief, vacuum relief, non-return)
Tank Construction:
- Inner tank 2.0mm mild steel with vitreous enamel glassline coating.
- Sacrificial magnesium anode for anti-corrosion protection.
Documentation Attached:
- IPX4 water ingress test certificate.
- Earthing continuity verification report.
Pending Gaps:
- Clause 19 Abnormal Operation heating test report pending.
- BEE 5-Star Standing Loss energy rating certificate yet to be appended.`
  }
};

export const ComplianceGapAnalyzer: React.FC = () => {
  const [searchParams] = useSearchParams();
  const preselectedStd = searchParams.get('standard');

  const [standards, setStandards] = useState<any[]>([]);
  const [selectedStandardId, setSelectedStandardId] = useState<number>(1);
  const [documentTitle, setDocumentTitle] = useState('');
  const [documentText, setDocumentText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [gapResult, setGapResult] = useState<ComplianceGapData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'fulfilled' | 'partial' | 'missing'>('all');
  const [uploadingFile, setUploadingFile] = useState(false);

  // Load standards
  useEffect(() => {
    const loadStandards = async () => {
      try {
        const res = await api.getStandards({ limit: 50 });
        if (res.success && res.standards) {
          setStandards(res.standards);
          if (preselectedStd) {
            const found = res.standards.find((s: any) => s.id === Number(preselectedStd));
            if (found) setSelectedStandardId(found.id);
          } else if (res.standards.length > 0) {
            setSelectedStandardId(res.standards[0].id);
          }
        }
      } catch (e) {
        console.error('Failed to load standards for dropdown', e);
      }
    };
    loadStandards();
  }, [preselectedStd]);

  const loadSample = (key: 'ss_bottle' | 'water_heater') => {
    const sample = SAMPLE_SPECS[key];
    setDocumentTitle(sample.title);
    setDocumentText(sample.text);
    const matched = standards.find(s => s.standard_number.includes(sample.standard_number.split(':')[0]));
    if (matched) {
      setSelectedStandardId(matched.id);
    } else {
      setSelectedStandardId(sample.standard_id);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setDocumentTitle(file.name);
    setUploadingFile(true);
    setError(null);

    try {
      // Use backend parser for PDF, DOCX, TXT
      const res = await api.uploadDocument(file);
      if (res.success && res.extracted_text) {
        setDocumentText(res.extracted_text);
      } else {
        throw new Error(res.detail || 'Failed to extract text from document');
      }
    } catch (err: any) {
      console.warn('API upload failed, attempting local fallback if text file:', err);
      // Fallback for simple text files if API has issues
      if (file.type.includes('text') || file.name.endsWith('.txt')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          const content = event.target?.result as string;
          setDocumentText(content || '');
        };
        reader.readAsText(file);
      } else {
        setError(err.response?.data?.detail || 'Failed to extract text from document. Please ensure it is a valid PDF, DOCX, or TXT file.');
      }
    } finally {
      setUploadingFile(false);
    }
  };

  const runGapAnalysis = async () => {
    if (!documentText.trim()) {
      setError('Please provide or upload technical specification text for comparison.');
      return;
    }

    setAnalyzing(true);
    setError(null);
    try {
      const res = await api.analyzeCompliance({
        standard_id: selectedStandardId,
        document_text: documentText,
        document_title: documentTitle || 'Uploaded Product Specification'
      });

      if (res.success) {
        setGapResult(res);
      } else {
        setError(res.detail || 'Failed to complete gap analysis.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Compliance gap analysis service encountered an error.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-5">
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">
          <FileCheck className="w-4 h-4" />
          <span>Automated Clause Verification Engine</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Compliance Gap & Readiness Analyzer
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload product specifications, test reports, or technical drawings to perform deterministic clause-by-clause comparison against mandatory BIS requirements.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Input Panel (5 columns) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              1. Select Target Indian Standard
            </h2>

            <div className="relative">
              <select
                value={selectedStandardId}
                onChange={(e) => setSelectedStandardId(Number(e.target.value))}
                className="w-full text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-600 appearance-none pr-8 cursor-pointer"
              >
                {standards.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.standard_number} — {s.title.substring(0, 45)}...
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            <div className="pt-2">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  2. Technical Documentation
                </h2>
                <div className="flex items-center space-x-1.5 text-[11px]">
                  <span className="text-slate-400">Presets:</span>
                  <button
                    onClick={() => loadSample('ss_bottle')}
                    className="text-emerald-700 hover:text-emerald-800 font-semibold underline"
                  >
                    SS Bottle
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    onClick={() => loadSample('water_heater')}
                    className="text-emerald-700 hover:text-emerald-800 font-semibold underline"
                  >
                    Water Heater
                  </button>
                </div>
              </div>

              {/* Upload Dropzone */}
              <label className={`border-2 border-dashed rounded-lg p-3 flex flex-col items-center justify-center cursor-pointer transition-colors mb-3 ${
                uploadingFile
                  ? 'border-emerald-500 bg-emerald-50/50'
                  : 'border-slate-200 hover:border-emerald-500 bg-slate-50 hover:bg-emerald-50/30'
              }`}>
                {uploadingFile ? (
                  <>
                    <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin mb-1" />
                    <span className="text-xs font-semibold text-emerald-800">Extracting document text...</span>
                    <span className="text-[10px] text-emerald-600">Parsing technical clauses</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-6 h-6 text-slate-400 mb-1" />
                    <span className="text-xs font-medium text-slate-700">Upload Spec Sheet or Test Report</span>
                    <span className="text-[10px] text-slate-400">PDF, DOCX, or TXT file</span>
                  </>
                )}
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileUpload}
                  disabled={uploadingFile}
                  className="hidden"
                />
              </label>

              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Document Title / Spec Reference ID"
                  value={documentTitle}
                  onChange={(e) => setDocumentTitle(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-emerald-600 bg-slate-50/50"
                />

                <textarea
                  rows={12}
                  placeholder="Paste specification details, bill of materials, test reports, or marking descriptions here..."
                  value={documentText}
                  onChange={(e) => setDocumentText(e.target.value)}
                  className="w-full p-3 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 font-mono leading-relaxed"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={runGapAnalysis}
              disabled={analyzing}
              className="w-full flex items-center justify-center space-x-2 py-3 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold shadow-sm transition-all disabled:opacity-50"
            >
              {analyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Comparing Against Mandatory Clauses...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Run Compliance Gap Audit</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Panel (7 columns) */}
        <div className="lg:col-span-7">
          {!gapResult ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center h-full flex flex-col items-center justify-center">
              <FileCheck className="w-12 h-12 text-slate-300 mb-3" />
              <h3 className="text-sm font-bold text-slate-800">No Gap Analysis Generated Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1 leading-relaxed">
                Select an Indian Standard, paste or upload your technical documentation on the left, and click <strong>Run Compliance Gap Audit</strong>.
              </p>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => {
                    loadSample('ss_bottle');
                    setTimeout(() => runGapAnalysis(), 100);
                  }}
                  className="px-3 py-1.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded text-xs font-medium hover:bg-emerald-100"
                >
                  ⚡ Try SS Bottle Demo
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Readiness Score Card */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Evaluated Against {gapResult.standard_number}
                    </span>
                    <h2 className="text-base font-bold text-slate-900 mt-0.5">
                      {gapResult.standard_title}
                    </h2>
                  </div>

                  <div className="flex items-center space-x-3 shrink-0">
                    <div>
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                        gapResult.risk_level === 'Low'
                          ? 'bg-emerald-100 text-emerald-800'
                          : gapResult.risk_level === 'Medium'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {gapResult.risk_level} Risk
                      </span>
                    </div>
                  </div>
                </div>

                {/* Verifiable Checklist Breakdown (replaces arbitrary percentage) */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                  <div className="bg-slate-50 rounded-lg p-3 text-center border border-slate-200">
                    <div className="text-lg font-black text-slate-900">
                      {gapResult.fulfilled_requirements.length + gapResult.missing_requirements.length + (gapResult.partial_requirements?.length || 0)}
                    </div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mt-0.5">
                      Requirements Assessed
                    </div>
                  </div>
                  <div className="bg-emerald-50 rounded-lg p-3 text-center border border-emerald-200">
                    <div className="text-lg font-black text-emerald-700">
                      {gapResult.fulfilled_requirements.length}
                    </div>
                    <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider mt-0.5">
                      Verified Fulfilled
                    </div>
                  </div>
                  <div className="bg-red-50 rounded-lg p-3 text-center border border-red-200">
                    <div className="text-lg font-black text-red-700">
                      {gapResult.missing_requirements.length}
                    </div>
                    <div className="text-[10px] font-bold text-red-600 uppercase tracking-wider mt-0.5">
                      Potential Gaps
                    </div>
                  </div>
                  <div className="bg-amber-50 rounded-lg p-3 text-center border border-amber-200">
                    <div className="text-lg font-black text-amber-700">
                      {gapResult.partial_requirements?.length || 0}
                    </div>
                    <div className="text-[10px] font-bold text-amber-600 uppercase tracking-wider mt-0.5">
                      Partially Met / Unassessable
                    </div>
                  </div>
                </div>

                {/* Compact progress bar with disclaimer */}
                <div className="mt-3">
                  <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                    <span className="font-semibold">Computed Readiness Estimate</span>
                    <span className="font-bold text-slate-700">{gapResult.compliance_percentage}%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        gapResult.compliance_percentage > 70
                          ? 'bg-emerald-600'
                          : gapResult.compliance_percentage > 40
                          ? 'bg-amber-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${gapResult.compliance_percentage}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 italic">
                    Based on {gapResult.fulfilled_requirements.length + gapResult.missing_requirements.length + (gapResult.partial_requirements?.length || 0)} verified requirements.
                    This is an automated estimate — refer to individual clause assessments above for authoritative detail.
                  </p>
                </div>
              </div>

              {/* Requirement Tabs */}
              <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div className="flex border-b border-slate-200 bg-slate-50/50 text-xs font-semibold">
                  <button
                    onClick={() => setActiveTab('all')}
                    className={`px-4 py-3 transition-colors border-b-2 ${
                      activeTab === 'all'
                        ? 'border-emerald-700 text-emerald-800 bg-white'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    All Requirements ({gapResult.fulfilled_requirements.length + gapResult.missing_requirements.length + (gapResult.partial_requirements?.length || 0)})
                  </button>
                  <button
                    onClick={() => setActiveTab('fulfilled')}
                    className={`px-4 py-3 transition-colors border-b-2 flex items-center space-x-1.5 ${
                      activeTab === 'fulfilled'
                        ? 'border-emerald-700 text-emerald-800 bg-white'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Fulfilled ({gapResult.fulfilled_requirements.length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('partial')}
                    className={`px-4 py-3 transition-colors border-b-2 flex items-center space-x-1.5 ${
                      activeTab === 'partial'
                        ? 'border-amber-600 text-amber-800 bg-white'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    <span>Partial ({gapResult.partial_requirements?.length || 0})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('missing')}
                    className={`px-4 py-3 transition-colors border-b-2 flex items-center space-x-1.5 ${
                      activeTab === 'missing'
                        ? 'border-red-600 text-red-800 bg-white'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <XCircle className="w-3.5 h-3.5 text-red-500" />
                    <span>Missing Gaps ({gapResult.missing_requirements.length})</span>
                  </button>
                </div>

                <div className="p-4 space-y-3 max-h-[480px] overflow-y-auto">
                  {/* Fulfilled */}
                  {(activeTab === 'all' || activeTab === 'fulfilled') &&
                    gapResult.fulfilled_requirements.map((req: any, idx: number) => (
                      <div
                        key={`f-${idx}`}
                        className="p-3.5 bg-emerald-50/40 border border-emerald-200 rounded-lg text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center text-emerald-800 font-bold space-x-1">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            <span>{req.id || `REQ-F${idx + 1}`}</span>
                          </span>
                          <span className="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-semibold uppercase">
                            Fulfilled
                          </span>
                        </div>
                        <p className="text-slate-800 font-medium">{req.description}</p>
                        {req.details?.matched_evidence && (
                          <p className="text-[11px] text-slate-600 font-mono bg-white p-2 rounded border border-emerald-100">
                            Evidence: {req.details.matched_evidence}
                          </p>
                        )}
                      </div>
                    ))}

                  {/* Partial */}
                  {(activeTab === 'all' || activeTab === 'partial') &&
                    gapResult.partial_requirements?.map((req: any, idx: number) => (
                      <div
                        key={`p-${idx}`}
                        className="p-3.5 bg-amber-50/40 border border-amber-200 rounded-lg text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center text-amber-800 font-bold space-x-1">
                            <AlertTriangle className="w-4 h-4 text-amber-600" />
                            <span>{req.id || `REQ-P${idx + 1}`}</span>
                          </span>
                          <span className="text-[10px] bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-semibold uppercase">
                            Partially Fulfilled
                          </span>
                        </div>
                        <p className="text-slate-800 font-medium">{req.description}</p>
                        {req.details?.missing_parameters && (
                          <p className="text-[11px] text-amber-900 font-mono bg-white p-2 rounded border border-amber-100">
                            Missing: {req.details.missing_parameters}
                          </p>
                        )}
                      </div>
                    ))}

                  {/* Missing */}
                  {(activeTab === 'all' || activeTab === 'missing') &&
                    gapResult.missing_requirements.map((req: any, idx: number) => (
                      <div
                        key={`m-${idx}`}
                        className="p-3.5 bg-red-50/40 border border-red-200 rounded-lg text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center text-red-800 font-bold space-x-1">
                            <XCircle className="w-4 h-4 text-red-600" />
                            <span>{req.id || `REQ-M${idx + 1}`}</span>
                          </span>
                          <span className="text-[10px] bg-red-100 text-red-800 px-2 py-0.5 rounded font-semibold uppercase">
                            Critical Gap
                          </span>
                        </div>
                        <p className="text-slate-900 font-semibold">{req.description}</p>
                        <p className="text-[11px] text-red-700">
                          Mandatory compliance requirement under BIS Scheme rules. Must be resolved before licence application.
                        </p>
                      </div>
                    ))}
                </div>
              </div>

              {/* Recommendations Roadmap */}
              {gapResult.recommendations && gapResult.recommendations.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-emerald-600" />
                    <span>Actionable Compliance Roadmap</span>
                  </h3>
                  <ul className="space-y-2">
                    {gapResult.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start space-x-2 text-xs text-slate-700">
                        <span className="font-bold text-emerald-700 shrink-0">{i + 1}.</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
