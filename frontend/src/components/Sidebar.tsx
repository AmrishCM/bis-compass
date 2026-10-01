import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Sparkles,
  ShieldCheck,
  BookOpen,
  FileCheck,
  Building2,
  Database,
  UploadCloud,
  BarChart3,
  History,
  Settings
} from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';

export const Sidebar: React.FC = () => {
  const { t } = useLanguage();

  const NAV_ITEMS = [
    { to: '/', labelKey: 'nav_dashboard', defaultLabel: 'Dashboard', icon: LayoutDashboard },
    { to: '/analyze', labelKey: 'nav_analyze', defaultLabel: 'Product Intelligence', icon: Sparkles, badgeKey: 'nav_flagship' },
    { to: '/consumer', labelKey: 'nav_consumer', defaultLabel: 'Consumer & Hallmarking', icon: ShieldCheck, badgeKey: 'nav_new' },
    { to: '/standards', labelKey: 'nav_standards', defaultLabel: 'Standards Directory', icon: BookOpen },
    { to: '/compliance', labelKey: 'nav_compliance', defaultLabel: 'Compliance Gap Analyzer', icon: FileCheck },
    { to: '/laboratories', labelKey: 'nav_labs', defaultLabel: 'Testing Laboratories', icon: Building2 },
    { to: '/sources', labelKey: 'nav_sources', defaultLabel: 'Verified Sources', icon: Database },
    { to: '/documents', labelKey: 'nav_documents', defaultLabel: 'Document Ingestion', icon: UploadCloud },
    { to: '/evaluation', labelKey: 'nav_evaluation', defaultLabel: 'RAG Evaluation', icon: BarChart3, badgeKey: 'nav_sih' },
    { to: '/history', labelKey: 'nav_audit', defaultLabel: 'Audit Trail', icon: History },
    { to: '/settings', labelKey: 'nav_settings', defaultLabel: 'System Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 border-b border-slate-100">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          {t('nav_section_title', 'Compliance Navigation')}
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
                <span>{t(item.labelKey, item.defaultLabel)}</span>
              </div>
              {item.badgeKey && (
                <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded">
                  {t(item.badgeKey, item.badgeKey === 'nav_flagship' ? 'Flagship' : item.badgeKey === 'nav_new' ? 'New' : 'SIH')}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Official BIS Authority footer */}
      <div className="p-3 border-t border-slate-200 bg-slate-50 text-[11px] text-slate-500">
        <div className="font-semibold text-slate-700">{t('nav_authority_footer', 'BIS Act 2016 Compliant')}</div>
        <p className="mt-0.5 text-slate-500 text-[10px] leading-relaxed">
          {t('nav_authority_desc', 'Product certification under Schemes I, II & IV with verifiable source citations.')}
        </p>
      </div>
    </aside>
  );
};
