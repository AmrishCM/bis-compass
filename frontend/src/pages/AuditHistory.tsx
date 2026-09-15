import React, { useState, useEffect } from 'react';
import {
  History,
  Search,
  ShieldCheck,
  RefreshCw,
  Clock,
  Layers,
  Sparkles,
  ArrowRight,
  UserCheck
} from 'lucide-react';
import { api } from '../services/api';

export const AuditHistory: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await api.getAuditLogs({
        action: actionFilter || undefined,
        limit: 100
      });
      if (res.success && res.logs) {
        setLogs(res.logs);
      }
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [actionFilter]);

  const filteredLogs = logs.filter((log) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (log.query && log.query.toLowerCase().includes(q)) ||
      log.action.toLowerCase().includes(q) ||
      (log.selected_model && log.selected_model.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">
            <History className="w-4 h-4" />
            <span>Compliance Governance & Reproducibility</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Audit Trail & Execution Logs
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Immutable log of all product analyses, standard retrieval queries, model invocations, and citation validations.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="p-2 border border-slate-200 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors"
          title="Refresh Logs"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search queries, models, or audit events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent bg-slate-50/50"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none font-medium text-slate-700 cursor-pointer"
          >
            <option value="">All Event Types</option>
            <option value="PRODUCT_ANALYSIS">Product Analysis</option>
            <option value="COMPLIANCE_GAP">Compliance Gap</option>
            <option value="WEB_SEARCH">Web Search</option>
          </select>
          <span className="text-xs text-slate-400 font-medium whitespace-nowrap">
            {filteredLogs.length} events logged
          </span>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="py-20 text-center">
            <RefreshCw className="w-8 h-8 animate-spin text-emerald-600 mx-auto mb-3" />
            <p className="text-xs text-slate-500 font-medium">Retrieving audit records...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-12 text-center">
            <History className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-800">No audit events recorded yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              Audit logs are automatically written whenever a product analysis or standard query is performed.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[11px] font-bold">
                <tr>
                  <th className="py-3 px-4">Event & Timestamp</th>
                  <th className="py-3 px-4">User Query</th>
                  <th className="py-3 px-4">Selected LLM Model</th>
                  <th className="py-3 px-4">Retrieved Sources</th>
                  <th className="py-3 px-4 text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="font-bold text-slate-900 flex items-center space-x-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span>{log.action}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        {log.created_at ? new Date(log.created_at).toLocaleString() : 'Just now'}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-medium text-slate-800 max-w-md truncate">
                      {log.query || 'Product intelligence analysis'}
                    </td>

                    <td className="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                      {log.selected_model}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1">
                        {(log.retrieval_sources || []).slice(0, 3).map((src: string, i: number) => (
                          <span
                            key={i}
                            className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[10px] font-mono"
                          >
                            {src}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono font-semibold text-emerald-800 whitespace-nowrap">
                      {log.execution_time_ms} ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
