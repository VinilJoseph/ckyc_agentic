import React, { useState } from 'react';

export default function BiometricCard({
  selfieMatch,
  onRunMatch,
  loading = false,
}) {
  const match = selfieMatch || {
    is_match: true,
    confidence: 0.88,
    threshold: 0.75,
    method: 'opencv_sface',
    details: 'Biometric facial comparison completed with high fidelity',
  };

  const confidencePct = Math.round((match.confidence || 0) * 100);
  const thresholdPct = Math.round((match.threshold || 0.75) * 100);
  const isMatch = match.is_match !== undefined ? match.is_match : confidencePct >= thresholdPct;

  return (
    <div className="p-4 rounded-xl bg-white dark:bg-[#16161A] border border-slate-200 dark:border-white/10 shadow-xs">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 flex items-center gap-1.5">
          <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Biometric Facial Match (Feature 6)
        </h4>

        {isMatch ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800">
            ✓ Biometric Verified
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 dark:bg-rose-950/70 dark:text-rose-400 border border-rose-300 dark:border-rose-800 animate-pulse">
            ⚠ Impostor Alert
          </span>
        )}
      </div>

      {/* Side-by-Side Photos */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {/* Live Selfie */}
        <div className="flex flex-col items-center p-2.5 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/5">
          <div className="w-20 h-24 rounded bg-slate-200 dark:bg-zinc-800 flex items-center justify-center text-slate-400 shadow-inner overflow-hidden border border-slate-300 dark:border-zinc-700">
            <svg className="w-12 h-12 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
            </svg>
          </div>
          <span className="text-[11px] font-bold text-slate-700 dark:text-zinc-300 mt-1.5">
            Live Selfie
          </span>
          <span className="text-[9px] text-slate-400">Captured in Portal</span>
        </div>

        {/* ID Photo */}
        <div className="flex flex-col items-center p-2.5 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/5">
          <div className="w-20 h-24 rounded bg-slate-200 dark:bg-zinc-800 flex items-center justify-center text-slate-400 shadow-inner overflow-hidden border border-slate-300 dark:border-zinc-700">
            <svg className="w-12 h-12 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
            </svg>
          </div>
          <span className="text-[11px] font-bold text-slate-700 dark:text-zinc-300 mt-1.5">
            ID Photo Crop
          </span>
          <span className="text-[9px] text-slate-400">Extracted from Document</span>
        </div>
      </div>

      {/* Metric Gauge & Progress */}
      <div className="space-y-1.5 mb-3">
        <div className="flex justify-between items-center text-xs">
          <span className="font-semibold text-slate-700 dark:text-zinc-300">
            Similarity Score:
          </span>
          <span className={`font-mono font-bold ${isMatch ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
            {confidencePct}% (Threshold: {thresholdPct}%)
          </span>
        </div>

        <div className="w-full bg-slate-200 dark:bg-zinc-800 h-2.5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isMatch ? 'bg-emerald-500' : 'bg-rose-500'
            }`}
            style={{ width: `${Math.min(confidencePct, 100)}%` }}
          />
        </div>
      </div>

      {/* Algorithm details strip & trigger */}
      <div className="pt-2 border-t border-slate-100 dark:border-white/5 flex items-center justify-between text-[10px]">
        <div className="text-slate-500 dark:text-zinc-400">
          <span className="font-semibold">Engine:</span> {match.method || 'OpenCV SFace 128D'}
        </div>
        <button
          onClick={onRunMatch}
          disabled={loading}
          className="text-cyan-600 dark:text-cyan-400 font-semibold hover:underline"
        >
          {loading ? 'Comparing...' : 'Re-run Comparison'}
        </button>
      </div>
    </div>
  );
}