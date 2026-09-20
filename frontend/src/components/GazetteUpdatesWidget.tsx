import React, { useState, useEffect } from 'react';
import { Newspaper, RefreshCw, ExternalLink, AlertCircle, CheckCircle, ShieldAlert, Filter } from 'lucide-react';
import { api } from '../services/api';

export const GazetteUpdatesWidget: React.FC = () => {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filterMinistry, setFilterMinistry] = useState('ALL');
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const fetchGazette = async () => {
    try {
      setLoading(true);
      const res = await api.getGazetteUpdates({
        ministry: filterMinistry === 'ALL' ? undefined : filterMinistry,
      });
      if (res.success) {
        setNotifications(res.notifications || []);
      }
    } catch (e) {
      console.error('Failed to fetch gazette updates', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGazette();
  }, [filterMinistry]);

  const handleSync = async () => {
    try {
      setSyncing(true);
      const res = await api.triggerGazetteSync();
      if (res.success) {
        setSyncMessage(res.message);
        await fetchGazette();
        setTimeout(() => setSyncMessage(null), 4000);
      }
    } catch (e) {
      console.error('Failed to sync gazette pipeline', e);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-amber-50 text-amber-700 rounded-lg">
            <Newspaper className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-900">
                Real-Time Gazette & Standards Update Pipeline
              </h3>
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Live tracking of mandatory Quality Control Orders (QCOs) and BIS standard amendments.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Ministry Filter */}
          <select
            value={filterMinistry}
            onChange={(e) => setFilterMinistry(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-slate-50 font-medium focus:ring-1 focus:ring-amber-500 focus:outline-none"
          >
            <option value="ALL">All Ministries</option>
            <option value="DPIIT">DPIIT (Commerce)</option>
            <option value="Steel">Ministry of Steel</option>
            <option value="MeitY">MeitY (Electronics)</option>
            <option value="Textiles">Ministry of Textiles</option>
            <option value="Bureau of Indian Standards">BIS Amendments</option>
          </select>

          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center space-x-1 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin text-amber-600' : ''}`} />
            <span>{syncing ? 'Polling...' : 'Sync Feed'}</span>
          </button>
        </div>
      </div>

      {syncMessage && (
        <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center space-x-2">
          <CheckCircle className="h-4 w-4 text-emerald-600 shrink-0" />
          <span>{syncMessage}</span>
        </div>
      )}

      {/* Notifications List */}
      {loading ? (
        <div className="py-8 text-center text-xs text-slate-400 flex items-center justify-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />
          <span>Fetching latest gazette notifications...</span>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <div
              key={n.id}
              className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/60 hover:bg-white hover:border-slate-300 transition-all text-xs space-y-2"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-slate-900">{n.title}</span>
                  <span className="font-mono text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded">
                    {n.order_number}
                  </span>
                </div>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                    n.status.includes('Enforced')
                      ? 'bg-rose-100 text-rose-800'
                      : n.status.includes('Upcoming')
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}
                >
                  {n.status}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-slate-600 text-[11px]">
                <div>
                  <span className="font-semibold text-slate-500">Ministry:</span> {n.ministry}
                </div>
                <div>
                  <span className="font-semibold text-slate-500">Effective Date:</span>{' '}
                  <span className="font-mono font-medium text-slate-800">{n.effective_date}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-500">Covered Standards:</span>{' '}
                  <span className="font-mono font-bold text-indigo-700">
                    {n.standards.join(', ')}
                  </span>
                </div>
              </div>

              <p className="text-slate-600 line-clamp-2 text-[11px]">{n.summary}</p>

              <div className="pt-1 flex items-center justify-between">
                <span className="text-[10px] text-slate-400">
                  Products: <span className="text-slate-600">{n.products_covered}</span>
                </span>
                <a
                  href={n.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1 text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
                >
                  <span>Official Gazette Notice</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
