import React, { useState, useEffect } from 'react';
import {
  Building2,
  Search,
  MapPin,
  CheckCircle2,
  ExternalLink,
  Phone,
  Mail,
  ShieldCheck,
  Filter,
  Layers,
  FlaskConical,
  RefreshCw
} from 'lucide-react';
import { api, LaboratoryData } from '../services/api';

export const LaboratoryDirectory: React.FC = () => {
  const [labs, setLabs] = useState<LaboratoryData[]>([]);
  const [loading, setLoading] = useState(true);
  const [locationFilter, setLocationFilter] = useState('');
  const [scopeFilter, setScopeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchLabs = async () => {
    setLoading(true);
    try {
      const res = await api.getLaboratories({
        location: locationFilter || undefined,
        scope: scopeFilter || undefined,
        limit: 50
      });
      if (res.success && res.laboratories) {
        setLabs(res.laboratories);
      }
    } catch (err) {
      console.error('Failed to fetch laboratories:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchLabs();
    }, 200);
    return () => clearTimeout(timer);
  }, [locationFilter, scopeFilter]);

  const filteredLabs = labs.filter((lab) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      lab.lab_name.toLowerCase().includes(q) ||
      lab.location.toLowerCase().includes(q) ||
      lab.address.toLowerCase().includes(q) ||
      (lab.accredited_scopes || []).some((s) => s.toLowerCase().includes(q)) ||
      (lab.testing_facilities || []).some((f) => f.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">
            <Building2 className="w-4 h-4" />
            <span>Conformity Assessment Testing Infrastructure</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            BIS-Recognized & NABL Accredited Laboratories
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Verified testing laboratories recognized under the BIS Act 2016 for sample testing, conformity evaluation, and type approval.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => fetchLabs()}
            className="p-2 border border-slate-200 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors"
            title="Refresh Directory"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search laboratory name, city, test facilities, or scope (e.g., thermal, NTH, CPRI, Mysore)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent bg-slate-50/50"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          {/* Location filter */}
          <div className="flex items-center space-x-1.5 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
            <MapPin className="w-3.5 h-3.5 text-slate-400" />
            <span>City:</span>
            <select
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              className="bg-transparent font-medium text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Regions</option>
              <option value="Ghaziabad">Ghaziabad / NCR</option>
              <option value="Bangalore">Bangalore</option>
              <option value="Mysore">Mysore</option>
              <option value="Chennai">Chennai</option>
              <option value="Delhi">Delhi</option>
              <option value="Kolkata">Kolkata</option>
              <option value="Mumbai">Mumbai</option>
            </select>
          </div>

          {/* Scope filter */}
          <div className="flex items-center space-x-1.5 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
            <FlaskConical className="w-3.5 h-3.5 text-slate-400" />
            <span>Scope:</span>
            <select
              value={scopeFilter}
              onChange={(e) => setScopeFilter(e.target.value)}
              className="bg-transparent font-medium text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Scopes</option>
              <option value="Thermal">Thermal & Mechanical</option>
              <option value="Electrical">Electrical & Cables</option>
              <option value="Food">Food & Water</option>
              <option value="Polymer">Polymers & Plastics</option>
            </select>
          </div>
        </div>
      </div>

      {/* Laboratories Grid */}
      {loading && labs.length === 0 ? (
        <div className="py-20 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-600 mx-auto mb-3" />
          <p className="text-xs text-slate-500 font-medium">Retrieving verified BIS laboratory registry...</p>
        </div>
      ) : filteredLabs.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No testing laboratories found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
            Try broadening your location or scope filters to search nationwide testing facilities.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredLabs.map((lab) => (
            <div
              key={lab.id}
              className="bg-white border border-slate-200 hover:border-emerald-300 rounded-xl p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-900 bg-slate-100 px-2.5 py-1 rounded">
                      {lab.accreditation_body} Accredited
                    </span>
                    {lab.is_bis_recognized && (
                      <span className="inline-flex items-center text-[11px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                        <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                        BIS Recognized
                      </span>
                    )}
                  </div>

                  <span className="text-[10px] text-slate-400 font-mono">
                    {lab.bis_recognition_number || 'REG-BIS-NAT'}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-slate-900 leading-snug">
                  {lab.lab_name}
                </h3>

                <div className="flex items-center space-x-1.5 text-xs text-slate-500 mt-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span>{lab.location} — {lab.address}</span>
                </div>

                {/* Accredited scopes */}
                <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Accredited Testing Scopes
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(lab.accredited_scopes || []).map((sc, i) => (
                      <span
                        key={i}
                        className="text-[10px] bg-slate-50 border border-slate-200 text-slate-700 px-2 py-0.5 rounded"
                      >
                        {sc}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Testing facilities */}
                <div className="mt-2 space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Specialized Test Facilities
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    {(lab.testing_facilities || []).join(', ')}
                  </p>
                </div>
              </div>

              {/* Contact info footer */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                <div className="flex items-center space-x-3">
                  {lab.phone && (
                    <span className="flex items-center space-x-1">
                      <Phone className="w-3 h-3 text-slate-400" />
                      <span>{lab.phone}</span>
                    </span>
                  )}
                  {lab.email && (
                    <span className="flex items-center space-x-1">
                      <Mail className="w-3 h-3 text-slate-400" />
                      <span>{lab.email}</span>
                    </span>
                  )}
                </div>

                {lab.website && (
                  <a
                    href={lab.website}
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-700 hover:text-emerald-800 font-semibold flex items-center space-x-1 text-[11px]"
                  >
                    <span>Lab Portal</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
