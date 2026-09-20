import React, { useState, useMemo } from 'react';
import { Calculator, Clock, CheckCircle2, TrendingDown, DollarSign, Calendar, Info, Award } from 'lucide-react';

interface FeeTimelineCalculatorProps {
  initialTestsCount?: number;
  standardNumber?: string;
}

export const FeeTimelineCalculator: React.FC<FeeTimelineCalculatorProps> = ({
  initialTestsCount = 4,
  standardNumber = 'IS Standard',
}) => {
  const [enterpriseTier, setEnterpriseTier] = useState<'micro' | 'small' | 'medium' | 'large' | 'startup'>('micro');
  const [scheme, setScheme] = useState<'scheme_1' | 'crs' | 'fmcs'>('scheme_1');
  const [productionVolume, setProductionVolume] = useState<number>(50000); // units/year
  const [testsCount, setTestsCount] = useState<number>(initialTestsCount || 4);

  // Concession calculation based on official BIS Concession Policy
  const concessionRate = useMemo(() => {
    switch (enterpriseTier) {
      case 'micro':
      case 'startup':
        return 0.50; // 50% concession on application fee & marking fee
      case 'small':
        return 0.20; // 20% concession
      default:
        return 0.0;
    }
  }, [enterpriseTier]);

  const calculations = useMemo(() => {
    // Base standard BIS fee schedule (Domestic Scheme-I)
    let baseAppFee = scheme === 'fmcs' ? 25000 : 1000;
    let baseLicFee = scheme === 'fmcs' ? 10000 : 1000;
    let baseMarkingFee = scheme === 'crs' ? 0 : 45000; // Scheme-I minimum marking fee
    let inspectionFee = scheme === 'fmcs' ? 75000 : 7000; // 1 man-day inspection
    let labTestEst = testsCount * 8500; // approx ₹8,500 per mandatory test

    // Apply MSME concession to Application Fee and Minimum Marking Fee
    const discountAppFee = baseAppFee * (1 - concessionRate);
    const discountMarkingFee = baseMarkingFee * (1 - concessionRate);

    const totalBeforeDiscount = baseAppFee + baseLicFee + baseMarkingFee + inspectionFee + labTestEst;
    const totalPayable = discountAppFee + baseLicFee + discountMarkingFee + inspectionFee + labTestEst;
    const totalSavings = totalBeforeDiscount - totalPayable;

    // Timeline calculation in days
    let prepDays = 10;
    let auditDays = scheme === 'fmcs' ? 30 : 15;
    let testDays = testsCount > 5 ? 35 : 25;
    let grantDays = 15;
    let totalDays = prepDays + auditDays + testDays + grantDays;

    return {
      baseAppFee,
      discountAppFee,
      baseLicFee,
      baseMarkingFee,
      discountMarkingFee,
      inspectionFee,
      labTestEst,
      totalPayable,
      totalSavings,
      totalDays,
      phases: [
        { name: 'Documentation & QAP Prep', days: prepDays, range: `Day 1 - ${prepDays}` },
        { name: 'Factory Audit & Sampling', days: auditDays, range: `Day ${prepDays + 1} - ${prepDays + auditDays}` },
        { name: 'Lab Testing at BIS/NABL Lab', days: testDays, range: `Day ${prepDays + auditDays + 1} - ${prepDays + auditDays + testDays}` },
        { name: 'Verification & Grant of License', days: grantDays, range: `Day ${prepDays + auditDays + testDays + 1} - ${totalDays}` },
      ],
    };
  }, [enterpriseTier, scheme, testsCount, concessionRate]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-emerald-50 text-emerald-700 rounded-lg">
            <Calculator className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Interactive BIS Fee & Timeline Calculator
            </h3>
            <p className="text-xs text-slate-500">
              Estimates statutory BIS fees, lab test charges, and licensing schedules tailored to your enterprise tier.
            </p>
          </div>
        </div>

        {concessionRate > 0 && (
          <div className="flex items-center space-x-1.5 bg-emerald-100/70 border border-emerald-300 text-emerald-900 px-3 py-1 rounded-full text-xs font-bold shrink-0">
            <Award className="h-3.5 w-3.5 text-emerald-700" />
            <span>{(concessionRate * 100).toFixed(0)}% BIS MSME Concession Active</span>
          </div>
        )}
      </div>

      {/* Controls Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Enterprise Tier */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Enterprise Classification
          </label>
          <select
            value={enterpriseTier}
            onChange={(e) => setEnterpriseTier(e.target.value as any)}
            className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-slate-50 font-medium focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="micro">Micro Enterprise (50% Concession)</option>
            <option value="startup">Startup India / Women-led (50% Concession)</option>
            <option value="small">Small Enterprise (20% Concession)</option>
            <option value="medium">Medium Enterprise (Standard)</option>
            <option value="large">Large Enterprise (Standard)</option>
          </select>
        </div>

        {/* Scheme */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Certification Scheme
          </label>
          <select
            value={scheme}
            onChange={(e) => setScheme(e.target.value as any)}
            className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-slate-50 font-medium focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="scheme_1">Scheme-I (ISI Mark - Domestic)</option>
            <option value="crs">Compulsory Registration Scheme (CRS)</option>
            <option value="fmcs">FMCS (Foreign Manufacturer)</option>
          </select>
        </div>

        {/* Mandatory Tests Count */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Estimated Tests Required: <span className="font-bold text-emerald-800">{testsCount} Tests</span>
          </label>
          <input
            type="range"
            min={1}
            max={12}
            value={testsCount}
            onChange={(e) => setTestsCount(Number(e.target.value))}
            className="w-full accent-emerald-600 mt-2"
          />
        </div>
      </div>

      {/* Cost Breakdown & Timeline Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 pt-2">
        {/* Cost Breakdown Table */}
        <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
              Statutory & Lab Cost Breakdown
            </span>
            {calculations.totalSavings > 0 && (
              <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                Saved ₹{calculations.totalSavings.toLocaleString('en-IN')}
              </span>
            )}
          </div>

          <div className="space-y-2 text-xs divide-y divide-slate-100">
            <div className="flex justify-between pt-1">
              <span className="text-slate-600">Application Filing Fee:</span>
              <span className="font-mono font-medium text-slate-900">
                ₹{calculations.discountAppFee.toLocaleString('en-IN')}
                {concessionRate > 0 && (
                  <span className="line-through text-slate-400 text-[10px] ml-1">
                    ₹{calculations.baseAppFee.toLocaleString('en-IN')}
                  </span>
                )}
              </span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-slate-600">Annual License Fee:</span>
              <span className="font-mono font-medium text-slate-900">
                ₹{calculations.baseLicFee.toLocaleString('en-IN')}
              </span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-slate-600">Minimum Annual Marking Fee:</span>
              <span className="font-mono font-medium text-slate-900">
                ₹{calculations.discountMarkingFee.toLocaleString('en-IN')}
                {concessionRate > 0 && (
                  <span className="line-through text-slate-400 text-[10px] ml-1">
                    ₹{calculations.baseMarkingFee.toLocaleString('en-IN')}
                  </span>
                )}
              </span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-slate-600">Factory Audit & Inspection (1 man-day):</span>
              <span className="font-mono font-medium text-slate-900">
                ₹{calculations.inspectionFee.toLocaleString('en-IN')}
              </span>
            </div>

            <div className="flex justify-between pt-2">
              <span className="text-slate-600">Estimated Third-Party Lab Testing:</span>
              <span className="font-mono font-medium text-slate-900">
                ₹{calculations.labTestEst.toLocaleString('en-IN')}
              </span>
            </div>

            <div className="flex justify-between pt-3 border-t-2 border-slate-200 text-sm font-bold">
              <span className="text-slate-900">Total Estimated Outlay:</span>
              <span className="font-mono text-emerald-700 text-base">
                ₹{calculations.totalPayable.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>

        {/* Timeline Roadmap */}
        <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
              Estimated Licensing Timeline
            </span>
            <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
              ~{calculations.totalDays} Calendar Days
            </span>
          </div>

          <div className="space-y-2.5 pt-1">
            {calculations.phases.map((phase, idx) => (
              <div key={idx} className="relative pl-5 text-xs">
                <div className="absolute left-0 top-1 w-2.5 h-2.5 rounded-full bg-emerald-600 ring-2 ring-emerald-100" />
                <div className="flex justify-between font-semibold text-slate-800">
                  <span>{phase.name}</span>
                  <span className="text-[11px] font-mono text-slate-500">{phase.range}</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full mt-1 overflow-hidden">
                  <div
                    className="bg-emerald-600 h-full rounded-full"
                    style={{ width: `${(phase.days / calculations.totalDays) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <p className="text-[11px] text-slate-500 pt-2 italic flex items-center space-x-1">
            <Info className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <span>
              Timelines depend on rapid test report turnaround from the chosen NABL/BIS lab and swift rectification of factory audit observations.
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};
