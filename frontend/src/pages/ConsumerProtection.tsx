import React, { useState } from 'react';
import {
  ShieldCheck,
  Award,
  AlertTriangle,
  FileText,
  Search,
  CheckCircle2,
  ExternalLink,
  Copy,
  Download,
  Info,
  Smartphone,
  PhoneCall,
  Scale,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';

export const ConsumerProtection: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'huid' | 'cml' | 'grievance'>('huid');

  // HUID State
  const [huidInput, setHuidInput] = useState('');
  const [declaredPurity, setDeclaredPurity] = useState('22K');
  const [metalType, setMetalType] = useState('gold');
  const [huidResult, setHuidResult] = useState<any | null>(null);
  const [huidLoading, setHuidLoading] = useState(false);

  // CML State
  const [cmlInput, setCmlInput] = useState('');
  const [cmlStandard, setCmlStandard] = useState('');
  const [cmlResult, setCmlResult] = useState<any | null>(null);
  const [cmlLoading, setCmlLoading] = useState(false);

  // Grievance State
  const [grievanceForm, setGrievanceForm] = useState({
    consumer_name: '',
    consumer_phone: '',
    consumer_email: '',
    complaint_category: 'fake_isi_mark',
    product_name: '',
    standard_number: '',
    seller_name: '',
    seller_location: '',
    invoice_number: '',
    invoice_date: '',
    incident_description: '',
  });
  const [grievanceResult, setGrievanceResult] = useState<any | null>(null);
  const [grievanceLoading, setGrievanceLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Handlers
  const handleVerifyHUID = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!huidInput.trim()) return;
    setHuidLoading(true);
    try {
      const res = await api.verifyHUID({
        huid: huidInput,
        metal_type: metalType,
        declared_purity: declaredPurity,
      });
      setHuidResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setHuidLoading(false);
    }
  };

  const handleVerifyCML = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cmlInput.trim()) return;
    setCmlLoading(true);
    try {
      const res = await api.verifyCML({
        cml_number: cmlInput,
        standard_number: cmlStandard,
      });
      setCmlResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setCmlLoading(false);
    }
  };

  const handleDraftGrievance = async (e: React.FormEvent) => {
    e.preventDefault();
    setGrievanceLoading(true);
    try {
      const res = await api.draftGrievance(grievanceForm);
      if (res.success) {
        setGrievanceResult(res);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setGrievanceLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-emerald-800 to-teal-900 rounded-2xl p-6 text-white shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-emerald-300 text-xs font-bold uppercase tracking-wider mb-1">
              <ShieldCheck className="h-4 w-4" />
              <span>Consumer Protection & Hallmarking Module</span>
            </div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Verify Hallmarking, ISI Marks & File Complaints
            </h1>
            <p className="text-emerald-100 text-xs mt-1 max-w-2xl">
              Verify the authenticity of 6-digit HUID gold hallmarking, inspect BIS license (CML)
              numbers, and generate legally structured grievance notices under the BIS Act, 2016.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-emerald-700/60 border border-emerald-500/50 p-3 rounded-xl shrink-0">
            <Smartphone className="h-6 w-6 text-emerald-200" />
            <div className="text-xs">
              <div className="font-bold text-white">BIS Care App</div>
              <div className="text-emerald-200 text-[11px]">Official Govt Verification Tool</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 gap-4">
        <button
          onClick={() => setActiveTab('huid')}
          className={`pb-3 text-xs font-bold transition-colors flex items-center space-x-2 border-b-2 -mb-px ${
            activeTab === 'huid'
              ? 'border-emerald-600 text-emerald-800'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <Award className="h-4 w-4" />
          <span>HUID & Gold Hallmarking Verifier</span>
        </button>

        <button
          onClick={() => setActiveTab('cml')}
          className={`pb-3 text-xs font-bold transition-colors flex items-center space-x-2 border-b-2 -mb-px ${
            activeTab === 'cml'
              ? 'border-emerald-600 text-emerald-800'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          <span>ISI Mark & License (CML) Inspector</span>
        </button>

        <button
          onClick={() => setActiveTab('grievance')}
          className={`pb-3 text-xs font-bold transition-colors flex items-center space-x-2 border-b-2 -mb-px ${
            activeTab === 'grievance'
              ? 'border-emerald-600 text-emerald-800'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <Scale className="h-4 w-4" />
          <span>Grievance Redressal Assistant</span>
        </button>
      </div>

      {/* =========================================================================
          TAB 1: HUID VERIFIER
         ========================================================================= */}
      {activeTab === 'huid' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <div className="lg:col-span-1 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-slate-900">Check Hallmarking (HUID)</h2>
            <p className="text-xs text-slate-500">
              Enter the 6-character alphanumeric code engraved on your jewelry article.
            </p>

            <form onSubmit={handleVerifyHUID} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  6-Digit HUID Code
                </label>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="e.g. AB12CD"
                  value={huidInput}
                  onChange={(e) => setHuidInput(e.target.value.toUpperCase())}
                  className="w-full font-mono font-bold text-center text-lg uppercase tracking-widest border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Precious Metal
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setMetalType('gold')}
                    className={`py-2 text-xs font-bold rounded-lg border transition-all ${
                      metalType === 'gold'
                        ? 'bg-amber-50 border-amber-400 text-amber-900'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Gold (IS 1417)
                  </button>
                  <button
                    type="button"
                    onClick={() => setMetalType('silver')}
                    className={`py-2 text-xs font-bold rounded-lg border transition-all ${
                      metalType === 'silver'
                        ? 'bg-slate-100 border-slate-400 text-slate-900'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Silver (IS 2112)
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Declared Karat / Purity
                </label>
                <select
                  value={declaredPurity}
                  onChange={(e) => setDeclaredPurity(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-slate-50 font-medium"
                >
                  <option value="24K">24 Karat (999 Fineness - 99.9% pure)</option>
                  <option value="22K">22 Karat (916 Fineness - 91.6% pure)</option>
                  <option value="20K">20 Karat (833 Fineness - 83.3% pure)</option>
                  <option value="18K">18 Karat (750 Fineness - 75.0% pure)</option>
                  <option value="14K">14 Karat (585 Fineness - 58.5% pure)</option>
                  <option value="9K">9 Karat (375 Fineness - 37.5% pure)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={huidLoading}
                className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold shadow transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <Search className="h-4 w-4" />
                <span>{huidLoading ? 'Verifying...' : 'Verify HUID & Hallmarks'}</span>
              </button>
            </form>

            <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500">
              <span className="font-semibold text-slate-700">Advisory:</span> Always demand a cash
              memo/tax invoice containing the exact HUID code for legal dispute protection.
            </div>
          </div>

          {/* Results & 4 Signs Guide */}
          <div className="lg:col-span-2 space-y-4">
            {huidResult && (
              <div
                className={`p-5 rounded-xl border ${
                  huidResult.is_valid_format
                    ? 'bg-emerald-50/70 border-emerald-200'
                    : 'bg-rose-50 border-rose-200'
                } space-y-3`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {huidResult.is_valid_format ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-rose-600" />
                    )}
                    <span className="text-sm font-bold text-slate-900">
                      HUID Format Verification: {huidResult.huid}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      huidResult.is_valid_format
                        ? 'bg-emerald-200 text-emerald-900'
                        : 'bg-rose-200 text-rose-900'
                    }`}
                  >
                    {huidResult.is_valid_format ? 'VALID SYNTAX' : 'INVALID FORMAT'}
                  </span>
                </div>

                {huidResult.is_valid_format ? (
                  <div className="space-y-3 text-xs">
                    <p className="text-slate-700">
                      Standard Reference:{' '}
                      <span className="font-bold text-indigo-800">
                        {huidResult.standard_reference}
                      </span>
                    </p>

                    {huidResult.matched_declared_purity && (
                      <div className="p-3 bg-white rounded-lg border border-emerald-200 grid grid-cols-3 gap-2 text-center">
                        <div>
                          <span className="text-[10px] text-slate-400 font-semibold block">
                            Purity Grade
                          </span>
                          <span className="font-mono font-bold text-slate-900 text-sm">
                            {huidResult.matched_declared_purity.karat}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 font-semibold block">
                            Fineness Mark
                          </span>
                          <span className="font-mono font-bold text-emerald-700 text-sm">
                            {huidResult.matched_declared_purity.fineness}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 font-semibold block">
                            Pure Gold %
                          </span>
                          <span className="font-mono font-bold text-slate-900 text-sm">
                            {huidResult.matched_declared_purity.pure_percentage}%
                          </span>
                        </div>
                      </div>
                    )}

                    <div className="p-3 bg-white rounded-lg border border-slate-200 space-y-2">
                      <span className="font-bold text-slate-800 block">
                        Verify with Official BIS Registry:
                      </span>
                      <div className="flex flex-wrap gap-2">
                        <a
                          href={huidResult.verification_routes.bis_manakonline_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold"
                        >
                          <span>Manak Online HUID Registry</span>
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                        <a
                          href={huidResult.verification_routes.bis_care_app_deep_link}
                          className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold"
                        >
                          <Smartphone className="h-3.5 w-3.5" />
                          <span>Launch BIS Care App</span>
                        </a>
                      </div>
                      <p className="text-[11px] text-slate-500 pt-1">
                        {huidResult.verification_routes.verification_instruction}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-rose-700">{huidResult.error_message}</p>
                )}
              </div>
            )}

            {/* The 4 Mandatory Signs of Hallmarking */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900">
                  The 4 Mandatory Hallmarking Signs on Genuine Jewelry
                </h3>
                <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded">
                  IS 1417 Checklist
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[11px] flex items-center justify-center">
                      1
                    </span>
                    <span className="font-bold text-xs text-slate-800">BIS Standard Logo</span>
                  </div>
                  <p className="text-[11px] text-slate-600 pl-7">
                    The triangle BIS logo certifying statutory standard conformance.
                  </p>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[11px] flex items-center justify-center">
                      2
                    </span>
                    <span className="font-bold text-xs text-slate-800">Purity / Fineness Grade</span>
                  </div>
                  <p className="text-[11px] text-slate-600 pl-7">
                    Shows purity in Karats and fineness (e.g. 22K916, 18K750, 14K585).
                  </p>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[11px] flex items-center justify-center">
                      3
                    </span>
                    <span className="font-bold text-xs text-slate-800">AHC Identification Mark</span>
                  </div>
                  <p className="text-[11px] text-slate-600 pl-7">
                    Assaying & Hallmarking Centre identifier where the piece was tested.
                  </p>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[11px] flex items-center justify-center">
                      4
                    </span>
                    <span className="font-bold text-xs text-slate-800">6-Digit HUID Code</span>
                  </div>
                  <p className="text-[11px] text-slate-600 pl-7">
                    Unique alphanumeric laser engraving providing end-to-end batch traceability.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 2: CML / ISI MARK INSPECTOR
         ========================================================================= */}
      {activeTab === 'cml' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-slate-900">Inspect ISI License (CML)</h2>
            <p className="text-xs text-slate-500">
              Verify the 7 or 8-digit Certification Marks License number printed under the ISI mark.
            </p>

            <form onSubmit={handleVerifyCML} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  CML / License Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. CM/L-1234567 or 1234567"
                  value={cmlInput}
                  onChange={(e) => setCmlInput(e.target.value)}
                  className="w-full font-mono border border-slate-300 rounded-lg p-2.5 text-xs font-medium focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Indian Standard Number (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. IS 17802 or IS 694"
                  value={cmlStandard}
                  onChange={(e) => setCmlStandard(e.target.value)}
                  className="w-full font-mono border border-slate-300 rounded-lg p-2.5 text-xs font-medium focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={cmlLoading}
                className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold shadow transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <Search className="h-4 w-4" />
                <span>{cmlLoading ? 'Inspecting...' : 'Verify License Authenticity'}</span>
              </button>
            </form>
          </div>

          <div className="lg:col-span-2 space-y-4">
            {cmlResult && (
              <div
                className={`p-5 rounded-xl border ${
                  cmlResult.is_valid_format
                    ? 'bg-emerald-50/70 border-emerald-200'
                    : 'bg-rose-50 border-rose-200'
                } space-y-3`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {cmlResult.is_valid_format ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-rose-600" />
                    )}
                    <span className="text-sm font-bold text-slate-900">
                      License Status: {cmlResult.cml_number}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      cmlResult.is_valid_format
                        ? 'bg-emerald-200 text-emerald-900'
                        : 'bg-rose-200 text-rose-900'
                    }`}
                  >
                    {cmlResult.is_valid_format ? 'VALID CML FORMAT' : 'INVALID FORMAT'}
                  </span>
                </div>

                {cmlResult.is_valid_format ? (
                  <div className="space-y-3 text-xs">
                    <p className="text-slate-700">
                      Standard Conformance:{' '}
                      <span className="font-bold text-indigo-800">
                        {cmlResult.standard_info?.standard_number || 'Standard Stated on Product'}
                      </span>
                    </p>

                    <div className="p-3 bg-white rounded-lg border border-slate-200 space-y-2">
                      <span className="font-bold text-slate-800 block">
                        Verify Against Official BIS Portal:
                      </span>
                      <a
                        href={cmlResult.verification_portal_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold"
                      >
                        <span>Know Your ISI Portal</span>
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                      <p className="text-[11px] text-slate-500 pt-1">
                        {cmlResult.bis_care_app_route}
                      </p>
                    </div>

                    <div className="p-3 bg-white rounded-lg border border-slate-200 space-y-1.5">
                      <span className="font-bold text-slate-800 block">
                        Authentic ISI Mark Checklist:
                      </span>
                      {cmlResult.authenticity_indicators.map((ind: string, idx: number) => (
                        <div key={idx} className="flex items-start space-x-2 text-slate-600">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 mt-0.5 shrink-0" />
                          <span>{ind}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-rose-700">{cmlResult.error_message}</p>
                )}
              </div>
            )}

            {/* How to Spot Fake ISI Marks */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
              <h3 className="text-sm font-bold text-slate-900">
                How to Spot Fake or Unauthorized ISI Marks
              </h3>
              <div className="space-y-2 text-xs text-slate-600">
                <div className="p-3 rounded-lg border border-rose-100 bg-rose-50/40 flex items-start space-x-2.5">
                  <AlertTriangle className="h-4 w-4 text-rose-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-bold text-slate-800 block">Missing CML Number</span>
                    <span>
                      An authentic ISI mark MUST have the 7 or 8-digit CML number directly under the
                      mark. If it only has the word "ISI" or "IS 17802" without a CML number, it is
                      unauthorized.
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-lg border border-amber-100 bg-amber-50/40 flex items-start space-x-2.5">
                  <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-bold text-slate-800 block">Missing IS Standard Number</span>
                    <span>
                      The exact Indian Standard number (e.g., IS 17802) must be printed directly
                      above the mark.
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 3: GRIEVANCE REDRESSAL ASSISTANT
         ========================================================================= */}
      {activeTab === 'grievance' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Complaint Form */}
          <div className="lg:col-span-1 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-slate-900">Draft Legal Grievance</h2>
            <p className="text-xs text-slate-500">
              Generate an official complaint citing Section 14, 15 & 29 of the BIS Act, 2016.
            </p>

            <form onSubmit={handleDraftGrievance} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Complaint Category</label>
                <select
                  value={grievanceForm.complaint_category}
                  onChange={(e) =>
                    setGrievanceForm({ ...grievanceForm, complaint_category: e.target.value })
                  }
                  className="w-full border border-slate-300 rounded-lg p-2 bg-slate-50 font-medium"
                >
                  <option value="fake_isi_mark">Counterfeit / Fake ISI Mark</option>
                  <option value="hallmarking_fraud">Hallmarking Fraud / Fake HUID / Under-karat</option>
                  <option value="substandard_quality">Substandard Quality / Safety Failure</option>
                  <option value="qco_violation">Violation of Mandatory QCO</option>
                  <option value="overcharging">Overcharging on Hallmarking Fees</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Your Full Name</label>
                <input
                  type="text"
                  placeholder="e.g. Ramesh Kumar"
                  value={grievanceForm.consumer_name}
                  onChange={(e) =>
                    setGrievanceForm({ ...grievanceForm, consumer_name: e.target.value })
                  }
                  className="w-full border border-slate-300 rounded-lg p-2"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    placeholder="9876543210"
                    value={grievanceForm.consumer_phone}
                    onChange={(e) =>
                      setGrievanceForm({ ...grievanceForm, consumer_phone: e.target.value })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Email</label>
                  <input
                    type="email"
                    placeholder="name@mail.com"
                    value={grievanceForm.consumer_email}
                    onChange={(e) =>
                      setGrievanceForm({ ...grievanceForm, consumer_email: e.target.value })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Product Description</label>
                <input
                  type="text"
                  placeholder="e.g. 22K Gold Bangle or PVC Electric Cable 2.5 sq mm"
                  value={grievanceForm.product_name}
                  onChange={(e) =>
                    setGrievanceForm({ ...grievanceForm, product_name: e.target.value })
                  }
                  className="w-full border border-slate-300 rounded-lg p-2"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Merchant / Seller</label>
                  <input
                    type="text"
                    placeholder="e.g. Royal Jewelers Ltd"
                    value={grievanceForm.seller_name}
                    onChange={(e) =>
                      setGrievanceForm({ ...grievanceForm, seller_name: e.target.value })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">City / Location</label>
                  <input
                    type="text"
                    placeholder="e.g. Jaipur, Rajasthan"
                    value={grievanceForm.seller_location}
                    onChange={(e) =>
                      setGrievanceForm({ ...grievanceForm, seller_location: e.target.value })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Invoice / Bill No.</label>
                  <input
                    type="text"
                    placeholder="e.g. INV-2024-884"
                    value={grievanceForm.invoice_number}
                    onChange={(e) =>
                      setGrievanceForm({ ...grievanceForm, invoice_number: e.target.value })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Purchase Date</label>
                  <input
                    type="date"
                    value={grievanceForm.invoice_date}
                    onChange={(e) =>
                      setGrievanceForm({ ...grievanceForm, invoice_date: e.target.value })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Incident Narrative / Defect Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Describe what happened, e.g. tested at private lab and found to be only 18K instead of 22K billed, or product broke causing electric short circuit..."
                  value={grievanceForm.incident_description}
                  onChange={(e) =>
                    setGrievanceForm({ ...grievanceForm, incident_description: e.target.value })
                  }
                  className="w-full border border-slate-300 rounded-lg p-2"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={grievanceLoading}
                className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <Scale className="h-4 w-4" />
                <span>{grievanceLoading ? 'Drafting Notice...' : 'Generate Legal Grievance'}</span>
              </button>
            </form>
          </div>

          {/* Grievance Output & Portals */}
          <div className="lg:col-span-2 space-y-4">
            {grievanceResult ? (
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Generated Formal Complaint Letter
                    </h3>
                    <p className="text-xs text-slate-500 font-mono">
                      Complaint Ref: {grievanceResult.complaint_id}
                    </p>
                  </div>
                  <button
                    onClick={() => copyToClipboard(grievanceResult.formal_complaint_letter)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>{copied ? 'Copied!' : 'Copy Letter'}</span>
                  </button>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg font-mono text-[11px] text-slate-800 whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
                  {grievanceResult.formal_complaint_letter}
                </div>

                {/* Submission Channels */}
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                    Official Submission Portals
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {grievanceResult.submission_channels.map((chan: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1.5 text-xs"
                      >
                        <span className="font-bold text-slate-800 block">{chan.channel_name}</span>
                        <p className="text-[11px] text-slate-500">{chan.note}</p>
                        {chan.portal_url && (
                          <a
                            href={chan.portal_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1 text-emerald-700 hover:underline font-semibold text-[11px]"
                          >
                            <span>Open Portal</span>
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                        {chan.phone_helpline && (
                          <span className="font-bold text-indigo-700 text-[11px] block">
                            Dial: {chan.phone_helpline}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Evidence Checklist */}
                <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg space-y-1.5 text-xs">
                  <span className="font-bold text-amber-900 block">
                    Evidence to Attach with Your Complaint:
                  </span>
                  <ul className="list-disc list-inside space-y-1 text-amber-800 text-[11px]">
                    {grievanceResult.evidence_checklist.map((item: string, i: number) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <div className="bg-white p-8 rounded-xl border border-dashed border-slate-300 text-center space-y-3">
                <Scale className="h-10 w-10 text-slate-300 mx-auto" />
                <h3 className="text-sm font-bold text-slate-700">No Complaint Generated Yet</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Fill in the incident details on the left to generate an official legal complaint
                  notice formatted with statutory citations under the BIS Act, 2016.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
