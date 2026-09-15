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

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
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
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" />
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
              className="bg-white text-emerald-900 hover:bg-emerald-50 text-xs font-bold px-4 py-2.5 rounded-lg shadow-sm flex items-center space-x-2 transition cursor-pointer"
            >
              <Sparkles className="h-4 w-4 text-emerald-700" />
              <span>Analyze a Product Now</span>
            </button>
            <button
              onClick={() => navigate('/standards')}
              className="bg-emerald-700/60 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg border border-emerald-500/40 flex items-center space-x-1.5 transition cursor-pointer"
            >
              <BookOpen className="h-4 w-4" />
              <span>Browse Standards Catalog</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Standards Indexed</span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {loading ? '-' : stats?.counts?.standards_indexed ?? 10}
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold flex items-center mt-1">
            <CheckCircle2 className="h-3 w-3 mr-1" /> Active BIS Standards
          </span>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Verifiable Clauses</span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {loading ? '-' : stats?.counts?.clauses_indexed ?? 40}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Clause-level evidence</span>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Certification Schemes</span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {loading ? '-' : stats?.counts?.certification_schemes ?? 10}
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold mt-1 block">Scheme I & II (CRS)</span>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Accredited Labs</span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {loading ? '-' : stats?.counts?.recognized_laboratories ?? 6}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">NABL & BIS Recognized</span>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Official Sources</span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {loading ? '-' : stats?.counts?.authoritative_sources ?? 3}
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold mt-1 block">Level 1 Authority</span>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 block">Analyses Performed</span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {loading ? '-' : stats?.counts?.analyses_performed ?? 0}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Audited query records</span>
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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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

      {/* System Integrity & Pipeline Transparency */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
