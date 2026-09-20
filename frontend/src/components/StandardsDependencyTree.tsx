import React, { useState } from 'react';
import { GitBranch, Box, CheckCircle2, FlaskConical, Shield, Layers, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export interface DependencyItem {
  standard_number: string;
  title: string;
  relationship_type: string; // 'MATERIAL_STANDARD' | 'TEST_METHOD_STANDARD' | 'REGULATORY_DOCUMENT' | 'COMPONENT_STANDARD'
  role?: string;
  source_url?: string;
}

interface StandardsDependencyTreeProps {
  primaryStandard: {
    standard_number: string;
    title: string;
    status?: string;
  };
  dependencies: DependencyItem[];
}

export const StandardsDependencyTree: React.FC<StandardsDependencyTreeProps> = ({
  primaryStandard,
  dependencies,
}) => {
  const [expandedType, setExpandedType] = useState<string | null>(null);

  const materials = dependencies.filter((d) => d.relationship_type === 'MATERIAL_STANDARD');
  const testMethods = dependencies.filter((d) => d.relationship_type === 'TEST_METHOD_STANDARD');
  const components = dependencies.filter((d) => d.relationship_type === 'COMPONENT_STANDARD');
  const regulatory = dependencies.filter((d) => d.relationship_type === 'REGULATORY_DOCUMENT' || d.relationship_type === 'REFERENCED_STANDARD');

  const groups = [
    {
      type: 'MATERIAL_STANDARD',
      label: 'Raw Material Specifications',
      icon: Box,
      color: 'border-blue-200 bg-blue-50/50 text-blue-800',
      badgeColor: 'bg-blue-100 text-blue-700',
      items: materials,
      description: 'Mandatory steel, plastic, or chemical grade standards required for primary fabrication.',
    },
    {
      type: 'TEST_METHOD_STANDARD',
      label: 'Standard Test Methods',
      icon: FlaskConical,
      color: 'border-amber-200 bg-amber-50/50 text-amber-800',
      badgeColor: 'bg-amber-100 text-amber-700',
      items: testMethods,
      description: 'Specific testing protocols (tensile, thermal, food-contact migration) required for compliance.',
    },
    {
      type: 'COMPONENT_STANDARD',
      label: 'Component & Performance Norms',
      icon: Layers,
      color: 'border-purple-200 bg-purple-50/50 text-purple-800',
      badgeColor: 'bg-purple-100 text-purple-700',
      items: components,
      description: 'Sub-assembly, safety, and ingress protection specifications.',
    },
    {
      type: 'REGULATORY_DOCUMENT',
      label: 'System & Quality Assurance Plans',
      icon: Shield,
      color: 'border-emerald-200 bg-emerald-50/50 text-emerald-800',
      badgeColor: 'bg-emerald-100 text-emerald-700',
      items: regulatory,
      description: 'Mandatory quality management schemes (IS/ISO 9001) and Scheme of Testing and Inspection (STI).',
    },
  ].filter((g) => g.items.length > 0);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg">
            <GitBranch className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Related & Dependency Standards Mapping
            </h3>
            <p className="text-xs text-slate-500">
              Auto-surfaced raw materials, test methods, and safety frameworks linked to this product.
            </p>
          </div>
        </div>
        <span className="text-xs bg-slate-100 text-slate-700 font-semibold px-2.5 py-1 rounded-full">
          {dependencies.length} Connected Standards
        </span>
      </div>

      {/* Primary Root Node */}
      <div className="relative pl-6 pb-2 before:absolute before:left-2.5 before:top-4 before:bottom-0 before:w-0.5 before:bg-indigo-200">
        <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-700 uppercase tracking-wide">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span>Primary Product Standard (Root)</span>
        </div>
        <div className="mt-1.5 p-3 rounded-lg border border-indigo-200 bg-indigo-50/60 flex items-center justify-between">
          <div>
            <div className="font-mono font-bold text-sm text-indigo-900">
              {primaryStandard.standard_number}
            </div>
            <div className="text-xs text-slate-700 font-medium mt-0.5">
              {primaryStandard.title}
            </div>
          </div>
          <span className="text-[10px] bg-indigo-200/80 text-indigo-800 font-bold px-2 py-0.5 rounded">
            Primary
          </span>
        </div>
      </div>

      {/* Child Groups */}
      <div className="space-y-3 pl-6">
        {groups.length === 0 ? (
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-500 italic">
            No external material specifications or separate test method standards are referenced in this standard's clauses. All essential criteria are self-contained in the primary specification.
          </div>
        ) : (
          groups.map((grp) => {
          const Icon = grp.icon;
          const isExpanded = expandedType === grp.type || expandedType === null;

          return (
            <div key={grp.type} className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedType(expandedType === grp.type ? '' : grp.type)}
                className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 flex items-center justify-between text-left transition-colors"
              >
                <div className="flex items-center space-x-2.5">
                  <Icon className="h-4 w-4 text-slate-600" />
                  <span className="text-xs font-bold text-slate-800">{grp.label}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${grp.badgeColor}`}>
                    {grp.items.length}
                  </span>
                </div>
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4 text-slate-400" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-slate-400" />
                )}
              </button>

              {isExpanded && (
                <div className="p-3 bg-white space-y-2 border-t border-slate-100">
                  <p className="text-[11px] text-slate-500 italic pb-1">{grp.description}</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {grp.items.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-md border border-slate-100 bg-slate-50/70 hover:bg-white hover:border-slate-300 transition-all text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-slate-900">
                            {item.standard_number}
                          </span>
                          <span className="text-[9px] uppercase tracking-wider font-semibold text-slate-400">
                            {item.relationship_type.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="text-slate-700 mt-1 line-clamp-1 font-medium">
                          {item.title}
                        </div>
                        {item.role && (
                          <div className="text-[11px] text-slate-500 mt-1 flex items-center space-x-1">
                            <span className="font-semibold text-slate-600">Role:</span>
                            <span className="line-clamp-1">{item.role}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        }))}
      </div>
    </div>
  );
};
