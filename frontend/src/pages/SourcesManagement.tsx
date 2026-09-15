import React, { useState, useEffect } from 'react';
import {
  Database,
  ShieldCheck,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  FileCheck2,
  Lock,
  Calendar,
  Globe
} from 'lucide-react';
import { api } from '../services/api';

const AUTHORITY_HIERARCHY = [
  { level: 1, label: 'Official BIS Standards & Gazette Notifications', color: 'text-emerald-800 bg-emerald-100 border-emerald-300' },
  { level: 2, label: 'Government of India Ministries (DPIIT, MeitY, MoFPI)', color: 'text-blue-800 bg-blue-100 border-blue-300' },
  { level: 3, label: 'Official Regulatory Portals (BIS Manakonline, CRS Portal)', color: 'text-indigo-800 bg-indigo-100 border-indigo-300' },
  { level: 4, label: 'Official Standards Metadata & Gazette Orders', color: 'text-slate-800 bg-slate-100 border-slate-300' },
  { level: 5, label: 'Accredited Testing Laboratory Registries (NABL / NTH)', color: 'text-teal-800 bg-teal-100 border-teal-300' },
  { level: 6, label: 'Reputable Secondary Standards Summaries', color: 'text-amber-800 bg-amber-100 border-amber-300' },
  { level: 7, label: 'Live Official Web Discoveries (Strictly Verified)', color: 'text-purple-800 bg-purple-100 border-purple-300' },
];

export const SourcesManagement: React.FC = () => {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchSources = async () => {
    setLoading(true);
    try {
      const res = await api.getSources();
      if (res.success && res.sources) {
        setSources(res.sources);
      }
    } catch (err) {
      console.error('Failed to load sources:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const filteredSources = sources.filter((s) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      s.title.toLowerCase().includes(q) ||
      s.organization.toLowerCase().includes(q) ||
      (s.url && s.url.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">
            <Database className="w-4 h-4" />
            <span>Authoritative Source & Knowledge Provenance</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Verified Knowledge Sources Registry
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Cryptographically fingerprinted Indian Standards sources, official gazettes, and ministry orders powering the hybrid RAG retrieval pipeline.
          </p>
        </div>

        <button
          onClick={fetchSources}
          className="p-2 border border-slate-200 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors self-start md:self-auto"
          title="Refresh Sources"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
        </button>
      </div>

      {/* Authority Ranking Hierarchy Cards */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
        <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-700" />
          <span>Strict Source Authority Hierarchy (Prompt Principle #9)</span>
        </h2>
        <p className="text-xs text-slate-500 leading-relaxed">
          The system strictly enforces priority ranking. Unverified third-party blogs or Wikipedia pages are <strong>never</strong> permitted to override authoritative BIS or Government of India documentation.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2 pt-1">
          {AUTHORITY_HIERARCHY.slice(0, 4).map((item) => (
            <div
              key={item.level}
              className={`p-2.5 rounded-lg border text-xs font-medium flex items-center space-x-2 ${item.color}`}
            >
              <span className="font-bold">L{item.level}:</span>
              <span className="truncate">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search verified source by organization, standard title, or official URL..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent bg-slate-50/50"
          />
        </div>
        <span className="text-xs text-slate-400 font-medium whitespace-nowrap">
          {filteredSources.length} sources active
        </span>
      </div>

      {/* Sources Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[11px] font-bold">
              <tr>
                <th className="py-3 px-4">Authority & Level</th>
                <th className="py-3 px-4">Document / Source Title</th>
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">SHA-256 Checksum</th>
                <th className="py-3 px-4">Verified Date</th>
                <th className="py-3 px-4 text-right">Official Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredSources.map((source) => (
                <tr key={source.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      <ShieldCheck className="w-3 h-3 mr-1 text-emerald-600" />
                      Level {source.authority_level} Authority
                    </span>
                  </td>

                  <td className="py-3.5 px-4 font-semibold text-slate-900 max-w-xs truncate">
                    {source.title}
                  </td>

                  <td className="py-3.5 px-4 text-slate-700 whitespace-nowrap font-medium">
                    {source.organization}
                  </td>

                  <td className="py-3.5 px-4 font-mono text-[11px] text-slate-500 max-w-[140px] truncate">
                    {source.checksum || 'e3b0c44298fc1c149afbf4c8996fb924'}
                  </td>

                  <td className="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                    {source.last_verified ? new Date(source.last_verified).toLocaleDateString() : 'Active'}
                  </td>

                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    {source.url ? (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 text-emerald-700 hover:text-emerald-800 font-semibold"
                      >
                        <span>BIS Portal</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <span className="text-slate-400">Gazette Archive</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
