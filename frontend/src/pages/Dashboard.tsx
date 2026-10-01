import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  BookOpen,
  Building2,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Database,
  Search,
  FileCheck2,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';
import { GazetteUpdatesWidget } from '../components/GazetteUpdatesWidget';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await api.getStats();
        setStats(data);
      } catch (e) {
        console.error('Failed to load stats:', e);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  const SAMPLE_PRODUCTS = [
    {
      name: 'Stainless Steel Water Bottles',
      desc: 'Double-walled insulated bottles for household potable water storage',
      standard: 'IS 17526:2021',
      category: 'Drinkware & Flasks',
    },
    {
      name: 'Domestic Electric Storage Water Heater',
      desc: '25-liter capacity electric water heater, 2000W rated power, 230V AC',
      standard: 'IS 302-2-15:2009',
      category: 'Electrical Appliances',
    },
    {
      name: 'PVC Insulated Copper Cables',
      desc: 'Single core unsheathed cable 1100V for domestic building wiring',
      standard: 'IS 694:2010',
      category: 'Wires & Cables',
    },
    {
      name: 'Packaged Drinking Water (PET Bottled)',
      desc: 'Ozonated & RO purified drinking water packaged in 1-liter sealed PET bottles',
      standard: 'IS 14543:2024',
      category: 'Food & Potable Water',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-emerald-800 to-teal-900 rounded-xl p-6 text-white shadow-sm border border-emerald-700">
        <div className="max-w-3xl">
          <div className="inline-flex items-center space-x-1.5 bg-emerald-700/80 border border-emerald-500/50 rounded-full px-3 py-1 text-xs font-semibold mb-3">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" aria-hidden="true" />
            <span>Ministry of Consumer Affairs & Bureau of Indian Standards Intelligence</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Indian Standards & BIS Compliance Intelligence
          </h1>
          <p className="mt-2 text-sm text-emerald-100 leading-relaxed">
            Enter your product description to instantly determine applicable Indian Standards,
            mandatory Quality Control Orders (QCOs), licensing paths (ISI Mark / CRS), testing requirements,
            and BIS-recognized testing laboratories.
          </p>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={() => navigate('/analyze')}
              className="flex items-center justify-center px-6 py-3.5 border border-transparent rounded-md shadow-sm text-base font-medium text-emerald-800 bg-emerald-50 hover:bg-emerald-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 transition-colors duration-200 cursor-pointer"
            >
              <Sparkles className="w-4 h-4 mr-2" aria-hidden="true" />
              <span>{t('btn_analyze', 'Analyze a Product Now')}</span>
            </button>
            <button
              onClick={() => navigate('/standards')}
              className="flex items-center justify-center px-6 py-3.5 border border-transparent rounded-md shadow-sm text-white font-medium bg-emerald-600 hover:bg-emerald-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 transition-colors duration-200 cursor-pointer"
            >
              <BookOpen className="w-4 h-4 mr-2" aria-hidden="true" />
              <span>{t('nav_standards', 'Browse Standards Catalog')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row - 4 Column Modern Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Standards Monitored */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Total Standards Monitored
              </span>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                Active Catalog
              </span>
            </div>
            <div className="flex items-baseline space-x-2 mt-2">
              <span className="text-2xl font-black text-slate-900 tracking-tight">
                24,100+
              </span>
              <span className="text-xs font-semibold text-slate-400">
                (24.1K+)
              </span>
            </div>
            <p className="text-[11px] text-slate-600 mt-2 leading-relaxed">
              Total active Indian Standards (IS Codes) published in the official Bureau of Indian Standards catalog.
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
            <span className="text-emerald-700 font-semibold flex items-center">
              <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-emerald-600" aria-hidden="true" /> Live Monitored
            </span>
            <span className="text-slate-500 font-medium bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
              {loading ? '...' : `${stats?.dynamic_cache?.sources_cached ?? stats?.counts?.standards_indexed ?? 0} Sources Cached`}
            </span>
          </div>
        </div>

        {/* Card 2: Mandatory QCOs (Gazette Orders) */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Mandatory QCOs (Gazette)
              </span>
              <span className="text-[10px] font-bold text-red-700 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">
                Statutory
              </span>
            </div>
            <div className="flex items-baseline space-x-2 mt-2">
              <span className="text-2xl font-black text-slate-900 tracking-tight">
                700+ Products
              </span>
              <span className="text-xs font-semibold text-slate-400">
                (150+ QCOs)
              </span>
            </div>
            <p className="text-[11px] text-slate-600 mt-2 leading-relaxed">
              Products brought under compulsory certification via Central Gazette notifications by DPIIT, Steel, & MeitY.
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
            <span className="text-red-700 font-semibold flex items-center">
              <ShieldCheck className="h-3.5 w-3.5 mr-1 text-red-600" aria-hidden="true" /> Gazette Enforced
            </span>
            <span className="text-slate-500 font-medium bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
              {loading ? '...' : `${stats?.dynamic_cache?.qco_records_tracked ?? stats?.counts?.mandatory_qcos ?? 0} Active Orders Tracked`}
            </span>
          </div>
        </div>

        {/* Card 3: Certification Schemes */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Certification Schemes
              </span>
              <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
                Compliance
              </span>
            </div>
            <div className="flex items-baseline space-x-2 mt-2">
              <span className="text-2xl font-black text-slate-900 tracking-tight">
                6 Primary Schemes
              </span>
            </div>
            <p className="text-[11px] text-slate-600 mt-2 leading-relaxed">
              <strong className="text-slate-800">Scheme-I</strong> (ISI), <strong className="text-slate-800">Scheme-II</strong> (CRS), <strong className="text-slate-800">FMCS</strong>, <strong className="text-slate-800">Hallmarking</strong> (HUID), <strong className="text-slate-800">CoC</strong>, and <strong className="text-slate-800">LRS</strong>.
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
            <span className="text-indigo-700 font-semibold flex items-center">
              <Sparkles className="h-3.5 w-3.5 mr-1 text-indigo-600" aria-hidden="true" /> Multi-Scheme
            </span>
            <span className="text-slate-500 font-medium bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
              {loading ? '...' : `${stats?.counts?.certification_schemes ?? 6} Active Models`}
            </span>
          </div>
        </div>

        {/* Card 4: Recognized Laboratories */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Recognized Laboratories
              </span>
              <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                NABL & BIS
              </span>
            </div>
            <div className="flex items-baseline space-x-2 mt-2">
              <span className="text-2xl font-black text-slate-900 tracking-tight">
                Hundreds Nationwide
              </span>
            </div>
            <p className="text-[11px] text-slate-600 mt-2 leading-relaxed">
              Nationwide network of Central BIS, National Test House (NTH), CPRI, ERTL, CFTRI, and CIPET testing labs.
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
            <span className="text-amber-700 font-semibold flex items-center">
              <Building2 className="h-3.5 w-3.5 mr-1 text-amber-600" aria-hidden="true" /> Verified Testing
            </span>
            <span className="text-slate-500 font-medium bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
              {loading ? '...' : `${stats?.dynamic_cache?.labs_indexed ?? stats?.counts?.recognized_laboratories ?? 0} Labs Indexed`}
            </span>
          </div>
        </div>
      </div>

      {/* Flagship Test Cases */}
      <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-2xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Quick Test Benchmarks (Verified BIS Ground Truth)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any verified benchmark product to run the complete multi-agent compliance pipeline.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {SAMPLE_PRODUCTS.map((prod, idx) => (
            <div
              key={idx}
              onClick={() => navigate('/analyze', { state: { description: prod.desc } })}
              className="p-3.5 border border-slate-200 rounded-lg hover:border-emerald-500 hover:bg-emerald-50/40 transition cursor-pointer group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-900 group-hover:text-emerald-800">
                      {prod.name}
                    </span>
                    <span className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-medium">
                      {prod.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
                    "{prod.desc}"
                  </p>
                </div>
                <div className="shrink-0 text-right ml-3">
                  <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded border border-emerald-200 block">
                    {prod.standard}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-1 flex items-center justify-end group-hover:text-emerald-700">
                    Run <ArrowRight className="h-3 w-3 ml-0.5" />
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Real-Time Gazette & Standards Update Pipeline */}
      <GazetteUpdatesWidget />

      {/* System Integrity & Pipeline Transparency */}
      <div className="grid grid-cols-1 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200">
          <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs uppercase tracking-wider mb-2">
            <Database className="h-4 w-4 text-emerald-600" />
            <span>Hybrid Retrieval Architecture</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Combines PostgreSQL full-text search (BM25 lexical scoring) with pgvector semantic similarity,
            reranked with source authority weights (0.45 semantic, 0.30 lexical, 0.15 metadata, 0.10 authority).
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200">
          <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs uppercase tracking-wider mb-2">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span>Strict LLM Safety & Citation Guarantee</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            The platform enforces an explicit safe-abstention protocol. Standards numbers, clauses, and laboratory
            test limits are strictly retrieved from canonical Gazette records and never manufactured by the LLM.
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200">
          <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs uppercase tracking-wider mb-2">
            <Building2 className="h-4 w-4 text-emerald-600" />
            <span>NABL / BIS Laboratory Network</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Directly cross-references official National Test House (NTH), CPRI, ERTL, CFTRI, and CIPET
            accreditation schedules with turn-around estimates and proximity filtering.
          </p>
        </div>
      </div>
    </div>
  );
};
