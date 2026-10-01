import React from 'react';
import { Compass, ShieldCheck, Cpu, MessageSquare, Globe, Sun, Moon, Volume2 } from 'lucide-react';
import { useLanguage, SUPPORTED_LANGUAGES, SupportedLanguage } from '../i18n/LanguageContext';

interface NavbarProps {
  onOpenChat?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenChat }) => {
  const { language, setLanguage, t } = useLanguage();

  const applyDarkMode = (useDark: boolean) => {
    if (useDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Brand */}
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-700 flex items-center justify-center text-white shadow-xs">
              <Compass className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">{t('app_title', 'BIS-Compass')}</span>
                <span className="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2 py-0.5 rounded border border-emerald-300">
                  {t('sih_badge', 'SIH 2026 Prototype')}
                </span>
                <span className="hidden xl:inline-flex items-center space-x-1 bg-amber-50 text-amber-900 border border-amber-300 text-[10px] font-bold px-2 py-0.5 rounded-full">
                  <Volume2 className="h-3 w-3 text-amber-600" />
                  <span>{t('bhashini_badge', 'Bhashini NLTM Active')}</span>
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium hidden sm:block">
                {t('app_subtitle', 'AI-Powered Indian Standards & BIS Compliance Intelligence Platform')}
              </p>
            </div>
          </div>

          {/* System Indicators & Controls */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="hidden md:flex items-center space-x-1.5 bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1 text-xs text-slate-600">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Authoritative:</span>
              <span className="font-semibold text-slate-800">BIS Gazette</span>
            </div>

            <div className="hidden lg:flex items-center space-x-1.5 bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1 text-xs text-slate-600">
              <Cpu className="h-4 w-4 text-emerald-600" />
              <span>Model:</span>
              <span className="font-semibold text-slate-800">NVIDIA NIM</span>
            </div>

            {/* Dark Mode Toggle */}
            <div
              className="hidden lg:flex items-center space-x-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-600 transition cursor-pointer"
              onClick={() => {
                const isDark = document.documentElement.classList.contains('dark');
                localStorage.setItem('bis-compass-dark-mode', (!isDark).toString());
                applyDarkMode(!isDark);
              }}
            >
              {document.documentElement.classList.contains('dark') ? (
                <Sun className="h-4 w-4 text-amber-500" />
              ) : (
                <Moon className="h-4 w-4 text-slate-600" />
              )}
            </div>

            {/* Persistent Language Switcher with 11 Indian Languages */}
            <div className="flex items-center space-x-1.5 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded-md px-2.5 py-1.5 text-xs text-slate-800 transition shadow-2xs">
              <Globe className="h-3.5 w-3.5 text-emerald-700 shrink-0" />
              <select
                id="language-switcher"
                value={language}
                onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
                className="bg-transparent text-xs font-bold text-emerald-950 focus:outline-none cursor-pointer pr-1"
                aria-label="Select Interface Language"
              >
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.nativeName} ({lang.name})
                  </option>
                ))}
              </select>
            </div>

            {onOpenChat && (
              <button
                onClick={onOpenChat}
                className="flex items-center space-x-1.5 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold px-3.5 py-1.5 rounded-md transition shadow-xs cursor-pointer focus-visible:outline-none"
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span>{t('btn_ask_advisor', 'Ask Advisor')}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
