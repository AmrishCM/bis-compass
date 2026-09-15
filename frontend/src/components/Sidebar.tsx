import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Sparkles,
  BookOpen,
  FileCheck,
  Building2,
  Database,
  UploadCloud,
  BarChart3,
  History,
  Settings
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/analyze', label: 'Product Intelligence', icon: Sparkles, badge: 'Flagship' },
  { to: '/standards', label: 'Standards Directory', icon: BookOpen },
  { to: '/compliance', label: 'Compliance Gap Analyzer', icon: FileCheck },
  { to: '/laboratories', label: 'Testing Laboratories', icon: Building2 },
  { to: '/sources', label: 'Verified Sources', icon: Database },
  { to: '/documents', label: 'Document Ingestion', icon: UploadCloud },
  { to: '/evaluation', label: 'RAG Evaluation', icon: BarChart3, badge: 'SIH' },
  { to: '/history', label: 'Audit Trail', icon: History },
  { to: '/settings', label: 'System Settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 border-b border-slate-100">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Compliance Navigation
        </span>
      </div>

      <nav className="p-3 space-y-1 flex-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <div className="flex items-center space-x-2.5">
                <Icon className="h-4 w-4 shrink-0 text-slate-500 group-hover:text-slate-700" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Official BIS Authority footer */}
      <div className="p-3 border-t border-slate-200 bg-slate-50 text-[11px] text-slate-500">
        <div className="font-semibold text-slate-700">BIS Act 2016 Compliant</div>
        <p className="mt-0.5 text-slate-500 text-[10px] leading-relaxed">
          Product certification under Schemes I, II & IV with verifiable source citations.
        </p>
      </div>
    </aside>
  );
};
