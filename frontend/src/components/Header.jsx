import React from 'react';
import ThemeToggle from './ThemeToggle';

export default function Header({
  activeTenant,
  setActiveTenant,
  tenants = [
    { id: '00000000-0000-0000-0000-000000000001', name: 'Apex Financial LLC' },
    { id: '00000000-0000-0000-0000-000000000002', name: 'Beta Marketplace Corp' },
    { id: '00000000-0000-0000-0000-000000000003', name: 'Tenant Alpha Demo' },
  ],
  theme,
  toggleTheme,
  onOpenNewCaseModal,
  onOpenEmailModal,
  onOpenPortalModal,
  onOpenCredentialModal,
  activeView,
  setActiveView,
}) {
  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-white/85 dark:bg-[#0D0D10]/85 border-b border-slate-200 dark:border-white/10 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand & Status */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveView('dashboard')}
            className="flex items-center gap-2.5 text-left group"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-md group-hover:scale-105 transition-transform">
              CK
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 dark:text-white text-base tracking-tight leading-none">
                  CKYC Showcase
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800/50">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse mr-1" />
                  Live MVP
                </span>
              </div>
              <span className="text-[11px] text-slate-500 dark:text-zinc-400 hidden sm:block">
                eKYC Marketplace & Reviewer Workspace
              </span>
            </div>
          </button>

          {/* Navigation view tabs */}
          <nav className="hidden md:flex items-center ml-4 pl-4 border-l border-slate-200 dark:border-white/10 gap-1">
            <button
              onClick={() => setActiveView('dashboard')}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                activeView === 'dashboard'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-black shadow-sm'
                  : 'text-slate-600 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800'
              }`}
            >
              Case Queue
            </button>
            <button
              onClick={onOpenCredentialModal}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                activeView === 'credentials'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-black shadow-sm'
                  : 'text-slate-600 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800'
              }`}
            >
              Credential Card
            </button>
            <button
              onClick={onOpenPortalModal}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                activeView === 'portal'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-black shadow-sm'
                  : 'text-slate-600 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800'
              }`}
            >
              Applicant Portal
            </button>
          </nav>
        </div>

        {/* Tenant Switcher & Quick Actions */}
        <div className="flex items-center gap-2.5">
          {/* Tenant Selector */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-white/10">
            <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-zinc-500">Tenant:</span>
            <select
              value={activeTenant?.id}
              onChange={(e) => {
                const found = tenants.find((t) => t.id === e.target.value);
                if (found) setActiveTenant(found);
              }}
              className="bg-transparent text-xs font-medium text-slate-800 dark:text-zinc-200 outline-none cursor-pointer pr-1"
            >
              {tenants.map((t) => (
                <option key={t.id} value={t.id} className="bg-white dark:bg-zinc-900 text-slate-900 dark:text-white">
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* User Role Pill */}
          <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-200/80 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 border border-slate-300/50 dark:border-white/10">
            Reviewer
          </span>

          {/* Quick Action: Email Simulator */}
          <button
            onClick={onOpenEmailModal}
            title="Open Email Intake Simulator"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 border border-indigo-200 dark:border-indigo-800/40 transition-all shadow-sm"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span className="hidden sm:inline">Email Simulator</span>
          </button>

          {/* Quick Action: New Case */}
          <button
            onClick={onOpenNewCaseModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4" />
            </svg>
            <span>+ New Case</span>
          </button>

          {/* Theme Toggle */}
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        </div>
      </div>
    </header>
  );
}
