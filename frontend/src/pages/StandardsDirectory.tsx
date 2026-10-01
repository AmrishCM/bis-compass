import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  Search,
  Filter,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  FileText,
  Layers,
  ArrowRight,
  Sparkles,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';

interface StandardItem {
  id: number;
  standard_number: string;
  title: string;
  scope: string;
  status: string;
  edition: string;
  publication_date: string | null;
  effective_date: string | null;
  clause_count: number;
  scheme_count: number;
  source: {
    organization: string;
    authority_level: number;
    url: string | null;
  } | null;
}

export const StandardsDirectory: React.FC = () => {
  const navigate = useNavigate();
  const [standards, setStandards] = useState<StandardItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const [liveSynced, setLiveSynced] = useState(false);

  const fetchStandards = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getStandards({
        q: searchQuery.trim() || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        limit: 50
      });
      if (res && res.success) {
        setStandards(res.standards || []);
        setTotalCount(res.total || 0);
        setLiveSynced(res.live_synced || false);
      } else if (typeof res === 'string' && (res as string).includes('<!DOCTYPE')) {
        setError('Connected backend returned HTML. The server may still be deploying or spinning up.');
      } else {
        setStandards([]);
        setTotalCount(0);
      }
    } catch (err: any) {
      console.error('Failed to load standards:', err);
      setError('Unable to reach Indian Standards service. If on Render free tier, the server takes ~30-40s on cold start.');
    } finally {
      setLoading(false);
    }
  };

  const handleSeedDatabase = async () => {
    setIsSeeding(true);
    setError(null);
    try {
      await api.seedStandards();
      await fetchStandards();
    } catch (err: any) {
      console.error('Failed to seed standards catalog:', err);
      setError('Failed to seed standards database. Please ensure backend is reachable.');
    } finally {
      setIsSeeding(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchStandards();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, statusFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">
            <BookOpen className="w-4 h-4" />
            <span>Bureau of Indian Standards Catalog</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Indian Standards (IS) Directory
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Verified repository of canonical Indian Standards, clauses, test methods, and certification requirements.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {totalCount === 0 && (
            <button
              onClick={handleSeedDatabase}
              disabled={isSeeding}
              className="flex items-center space-x-1.5 px-3 py-2 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50"
              title="Seed canonical verified Indian Standards"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin' : ''}`} />
              <span>{isSeeding ? 'Seeding...' : 'Seed Standards'}</span>
            </button>
          )}
          <button
            onClick={() => fetchStandards()}
            className="p-2 border border-slate-200 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors"
            title="Refresh standards"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
          </button>
          <button
            onClick={() => navigate('/analyze')}
            className="flex items-center space-x-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-medium rounded-lg shadow-sm transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span>Match Product to Standard</span>
          </button>
        </div>
      </div>

      {/* Backend Alert / Cold Start Notice */}
      {error && (
        <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div>
              <p className="font-semibold">{error}</p>
              <p className="text-amber-700 text-[11px] mt-0.5">Free-tier instances may sleep after inactivity. Click Retry or Seed to reconnect.</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 self-end sm:self-auto">
            <button
              onClick={() => fetchStandards()}
              className="px-3 py-1.5 bg-amber-700 hover:bg-amber-800 text-white rounded font-medium transition-colors"
            >
              Retry
            </button>
            <button
              onClick={handleSeedDatabase}
              disabled={isSeeding}
              className="px-3 py-1.5 bg-white border border-amber-300 hover:bg-amber-100 text-amber-900 rounded font-medium transition-colors"
            >
              {isSeeding ? 'Seeding...' : 'Seed Catalog'}
            </button>
          </div>
        </div>
      )}

      {/* Live BIS Discovery Sync Notification */}
      {liveSynced && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl p-3 flex items-center space-x-2 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>
            <strong>Official BIS Live Sync:</strong> Fresh Indian Standards discovered in real-time from the official Bureau of Indian Standards Portal (<em>services.bis.gov.in</em>) and cached to repository.
          </span>
        </div>
      )}

      {/* Search & Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search standard number, title, or scope (e.g., IS 17526, stainless steel, water heater, cables)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent bg-slate-50/50"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <div className="flex items-center space-x-1.5 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent font-medium text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="all">All Standards</option>
              <option value="active">Active / Mandatory</option>
              <option value="under_revision">Under Revision</option>
            </select>
          </div>
          <span className="text-xs text-slate-400 font-medium px-2 whitespace-nowrap">
            {totalCount} standards indexed
          </span>
        </div>
      </div>

      {/* Standards List */}
      {loading && standards.length === 0 ? (
        <div className="py-20 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-600 mx-auto mb-3" />
          <p className="text-sm text-slate-500 font-medium">Querying authoritative BIS database...</p>
        </div>
      ) : standards.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">
            {searchQuery ? `No matching standards for "${searchQuery}" in directory` : 'No Indian Standards Currently Indexed'}
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
            {searchQuery
              ? 'Try searching by standard number (e.g., IS 17526, IS 4375, IS 694) or broader terms. The system will query the official BIS portal in real-time.'
              : 'Populate the verified repository with canonical Indian Standards, clauses, schemes, and recognized testing laboratories.'}
          </p>
          <div className="flex justify-center items-center gap-3">
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Clear Search
              </button>
            )}
            <button
              onClick={handleSeedDatabase}
              disabled={isSeeding}
              className="flex items-center space-x-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-medium rounded-lg shadow-sm transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin' : ''}`} />
              <span>{isSeeding ? 'Seeding Standards...' : 'Seed Canonical Standards Catalog'}</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {standards.map((std) => (
            <div
              key={std.id}
              className="bg-white rounded-xl border border-slate-200 hover:border-emerald-300 hover:shadow-md transition-all p-5 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-emerald-900 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded">
                      {std.standard_number}
                    </span>
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      Edition {std.edition}
                    </span>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    {std.status === 'active' ? (
                      <span className="inline-flex items-center text-[10px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                        <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" /> Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-[10px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                        Revision
                      </span>
                    )}
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-slate-900 leading-snug hover:text-emerald-700 transition-colors">
                  <Link to={`/standards/${std.id}`}>
                    {std.title}
                  </Link>
                </h3>

                <p className="text-xs text-slate-600 mt-2 line-clamp-3 leading-relaxed">
                  {std.scope}
                </p>

                {/* Metadata badges */}
                <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-slate-100 text-[11px] text-slate-500">
                  <span className="flex items-center space-x-1">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-semibold text-slate-700">{std.clause_count}</span>
                    <span>clauses</span>
                  </span>
                  <span className="text-slate-300">•</span>
                  <span className="flex items-center space-x-1">
                    <FileText className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-semibold text-slate-700">{std.scheme_count}</span>
                    <span>schemes</span>
                  </span>
                  <span className="text-slate-300">•</span>
                  <span className="flex items-center space-x-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Level 1 BIS Official</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 mt-4 pt-3 border-t border-slate-100">
                <Link
                  to={`/standards/${std.id}`}
                  className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center space-x-1"
                >
                  <span>Explore Clauses & Specs</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>

                <button
                  onClick={() => navigate(`/analyze?target=${encodeURIComponent(std.standard_number)}`)}
                  className="text-[11px] px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-medium transition-colors"
                >
                  Test Compliance
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
