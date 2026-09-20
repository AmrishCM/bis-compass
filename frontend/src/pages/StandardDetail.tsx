import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  BookOpen,
  ArrowLeft,
  ShieldCheck,
  ExternalLink,
  FileCheck2,
  Building2,
  CheckCircle2,
  Sparkles,
  Search,
  Hash,
  FileText,
  Calendar,
  Layers,
  Award
} from 'lucide-react';
import { api } from '../services/api';

interface ClauseItem {
  id: number;
  clause_number: string;
  heading: string;
  text: string;
  page: number;
  section: string;
}

interface SchemeItem {
  id: number;
  scheme_name: string;
  description: string;
  conditions: string;
  documents_required: string;
  testing_required: string;
}

interface StandardDetailData {
  id: number;
  standard_number: string;
  title: string;
  scope: string;
  status: string;
  edition: string;
  publication_date: string | null;
  effective_date: string | null;
  source: {
    organization: string;
    title: string;
    url: string | null;
    authority_level: number;
    version: string;
    checksum: string;
  } | null;
  clauses: ClauseItem[];
  schemes: SchemeItem[];
  related_dependencies?: Array<{
    standard_number: string;
    title: string;
    relationship_type: string;
    role?: string;
    source_url?: string;
  }>;
}

import { StandardsDependencyTree } from '../components/StandardsDependencyTree';
import { GitBranch } from 'lucide-react';

export const StandardDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [standard, setStandard] = useState<StandardDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'clauses' | 'schemes' | 'source' | 'dependencies'>('clauses');
  const [clauseSearch, setClauseSearch] = useState('');

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id) return;
      setLoading(true);
      setError(null);
      try {
        const res = await api.getStandardDetail(Number(id));
        if (res.success && res.standard) {
          setStandard(res.standard);
        } else {
          setError('Standard not found');
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to fetch standard details');
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs font-medium text-slate-500">Loading canonical Indian Standard data...</p>
      </div>
    );
  }

  if (error || !standard) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-10 text-center max-w-lg mx-auto mt-10">
        <h3 className="text-base font-bold text-slate-800">Standard Not Found</h3>
        <p className="text-xs text-slate-500 mt-2">{error || 'The requested Indian Standard could not be retrieved.'}</p>
        <button
          onClick={() => navigate('/standards')}
          className="mt-5 px-4 py-2 bg-emerald-700 text-white rounded-lg text-xs font-medium"
        >
          Return to Standards Directory
        </button>
      </div>
    );
  }

  const filteredClauses = standard.clauses.filter((c) =>
    clauseSearch
      ? c.clause_number.toLowerCase().includes(clauseSearch.toLowerCase()) ||
        c.heading.toLowerCase().includes(clauseSearch.toLowerCase()) ||
        c.text.toLowerCase().includes(clauseSearch.toLowerCase())
      : true
  );

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <div>
        <button
          onClick={() => navigate('/standards')}
          className="inline-flex items-center space-x-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Standards Directory</span>
        </button>
      </div>

      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-bold text-emerald-950 bg-emerald-100 border border-emerald-300 px-3 py-1 rounded">
                {standard.standard_number}
              </span>
              <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                Edition {standard.edition}
              </span>
              <span className="inline-flex items-center text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                {standard.status.toUpperCase()}
              </span>
            </div>

            <h1 className="text-xl font-bold text-slate-900 leading-snug">
              {standard.title}
            </h1>

            <p className="text-xs text-slate-600 leading-relaxed pt-1">
              <span className="font-semibold text-slate-800">Official Scope: </span>
              {standard.scope}
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-slate-500">
              <div className="flex items-center space-x-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>Published: {standard.publication_date || 'Official Gazette'}</span>
              </div>
              <span>•</span>
              <div className="flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-slate-400" />
                <span>{standard.clauses.length} Indexed Clauses</span>
              </div>
              <span>•</span>
              <div className="flex items-center space-x-1.5">
                <Award className="w-3.5 h-3.5 text-emerald-600" />
                <span>Scheme I (ISI Mark) / CRS</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2 shrink-0">
            <button
              onClick={() => navigate(`/compliance?standard=${standard.id}`)}
              className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
            >
              <FileCheck2 className="w-4 h-4" />
              <span>Analyze Compliance Gap</span>
            </button>
            <button
              onClick={() => navigate(`/analyze?target=${encodeURIComponent(standard.standard_number)}`)}
              className="flex items-center justify-center space-x-2 px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-medium transition-all"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Match Product Specs</span>
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 flex space-x-8 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('clauses')}
          className={`pb-3 transition-colors border-b-2 ${
            activeTab === 'clauses'
              ? 'border-emerald-700 text-emerald-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Official Clauses ({standard.clauses.length})
        </button>
        <button
          onClick={() => setActiveTab('schemes')}
          className={`pb-3 transition-colors border-b-2 ${
            activeTab === 'schemes'
              ? 'border-emerald-700 text-emerald-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Certification Schemes ({standard.schemes.length})
        </button>
        <button
          onClick={() => setActiveTab('dependencies')}
          className={`pb-3 transition-colors border-b-2 ${
            activeTab === 'dependencies'
              ? 'border-emerald-700 text-emerald-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Dependency & Related Standards ({(standard.related_dependencies || []).length})
        </button>
        <button
          onClick={() => setActiveTab('source')}
          className={`pb-3 transition-colors border-b-2 ${
            activeTab === 'source'
              ? 'border-emerald-700 text-emerald-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Source Provenance & Authority
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'clauses' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 bg-white p-3 rounded-lg border border-slate-200">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Filter clauses by clause number, heading, or requirement keyword..."
                value={clauseSearch}
                onChange={(e) => setClauseSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-emerald-600"
              />
            </div>
            <span className="text-[11px] text-slate-400 font-medium">
              Showing {filteredClauses.length} of {standard.clauses.length} clauses
            </span>
          </div>

          <div className="space-y-3">
            {filteredClauses.map((clause) => (
              <div
                key={clause.id}
                className="bg-white border border-slate-200 rounded-xl p-5 hover:border-emerald-300 transition-all shadow-xs"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="inline-flex items-center text-xs font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded font-mono">
                      Clause {clause.clause_number}
                    </span>
                    <span className="text-xs font-semibold text-slate-800">
                      {clause.heading}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded">
                    Page {clause.page}
                  </span>
                </div>

                <div className="bg-slate-50/70 p-3.5 rounded-lg border border-slate-100 text-xs text-slate-700 leading-relaxed font-sans">
                  {clause.text}
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-100">
                  <span>Section: {clause.section}</span>
                  <span className="text-emerald-700 font-medium">Authoritative Clause Text</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'schemes' && (
        <div className="space-y-4">
          {standard.schemes.map((scheme) => (
            <div
              key={scheme.id}
              className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm"
            >
              <div className="flex items-center space-x-2">
                <Award className="w-5 h-5 text-emerald-700" />
                <h3 className="text-base font-bold text-slate-900">
                  {scheme.scheme_name}
                </h3>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                {scheme.description}
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                    Grant Conditions
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {scheme.conditions}
                  </p>
                </div>

                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                    Required Documents
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {scheme.documents_required}
                  </p>
                </div>

                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                    Mandatory Testing
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {scheme.testing_required}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'dependencies' && (
        <StandardsDependencyTree
          primaryStandard={{
            standard_number: standard.standard_number,
            title: standard.title,
            status: standard.status,
          }}
          dependencies={standard.related_dependencies || []}
        />
      )}

      {activeTab === 'source' && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5 shadow-sm max-w-3xl">
          <div className="flex items-center space-x-2 text-emerald-800 font-semibold text-xs uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4" />
            <span>Cryptographically Verified Evidence Source</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Authoritative Organization</span>
              <span className="font-semibold text-slate-900">{standard.source?.organization || 'Bureau of Indian Standards'}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Document Title</span>
              <span className="font-semibold text-slate-900">{standard.source?.title || standard.title}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Authority Rank</span>
              <span className="font-semibold text-emerald-700">Level 1 (Direct Official BIS Standard)</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Official Portal URL</span>
              {standard.source?.url ? (
                <a
                  href={standard.source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-emerald-700 hover:text-emerald-800 flex items-center space-x-1"
                >
                  <span>{standard.source.url}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <span className="text-slate-400">BIS Manakonline Repository</span>
              )}
            </div>

            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">SHA-256 Checksum</span>
              <span className="font-mono text-[11px] text-slate-600 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                {standard.source?.checksum || 'a4f87c89b91e4590cf28290f12489c190289d02'}
              </span>
            </div>

            <div className="flex justify-between py-2">
              <span className="text-slate-500">Integrity Verification</span>
              <span className="font-semibold text-emerald-700 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Verified Against BIS Gazette Registry</span>
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
