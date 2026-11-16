import React, { useState } from 'react';

export default function DecisionBar({
  caseStatus,
  onApprove,
  onReject,
  onRequestCorrection,
  onAdvanceToReview,
  loading = false,
}) {
  const [justification, setJustification] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const quickChips = [
    'All identity documents verified, Verhoeff checksum valid, and biometric match confirmed.',
    'Suspected fraudulent submission: invalid PAN structure and failed facial comparison.',
    'Missing clear back side of identity document; requesting applicant re-upload.',
  ];

  const handleChipClick = (chipText) => {
    setJustification(chipText);
    setErrorMsg('');
  };

  const handleApprove = () => {
    if (!justification.trim()) {
      setErrorMsg('Mandatory written justification reason is required to approve the case.');
      return;
    }
    setErrorMsg('');
    onApprove(justification.trim());
  };

  const handleReject = () => {
    if (!justification.trim()) {
      setErrorMsg('Mandatory written justification reason is required to reject the case.');
      return;
    }
    setErrorMsg('');
    onReject(justification.trim());
  };

  const isTerminal = ['approved', 'rejected', 'closed', 'expired'].includes(caseStatus);
  const isInReview = caseStatus === 'in_review';
  const hasJustification = justification.trim().length > 0;

  return (
    <div className="sticky bottom-0 z-20 backdrop-blur-md bg-white/95 dark:bg-[#16161A]/95 border-t border-slate-200 dark:border-white/10 p-4 shadow-lg transition-colors">
      <div className="max-w-4xl mx-auto space-y-3">
        {/* Terminal Status Warning Banner */}
        {isTerminal && (
          <div className="p-3 rounded-lg bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 text-xs font-semibold flex items-center justify-between">
            <span>
              This case is in terminal status: <strong className="uppercase">{caseStatus}</strong>. Further approval/rejection decisions are locked.
            </span>
          </div>
        )}

        {/* Advance to In-Review Action if in draft or documents_received */}
        {!isTerminal && !isInReview && (
          <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/40 flex items-center justify-between text-xs">
            <span className="text-amber-800 dark:text-amber-300 font-medium">
              Case status is currently <strong>{caseStatus}</strong>. Advance to <strong>In Review</strong> to enable final approval/rejection gates.
            </span>
            <button
              onClick={onAdvanceToReview}
              disabled={loading}
              className="px-3 py-1 rounded-full text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-xs"
            >
              Advance to In Review →
            </button>
          </div>
        )}

        {!isTerminal && (
          <>
            {/* Quick-fill justification chips */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-zinc-500 mr-1">
                Preset Rationale:
              </span>
              {quickChips.map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => handleChipClick(chip)}
                  type="button"
                  className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 hover:text-cyan-700 dark:hover:text-cyan-300 border border-slate-200 dark:border-white/5 transition-all truncate max-w-[260px]"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Justification Textarea */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-bold text-slate-700 dark:text-zinc-300 flex items-center gap-1">
                  Reviewer Justification & Audit Rationale
                  <span className="text-rose-500 font-black">*</span>
                </label>
                <span className="text-[10px] text-slate-400 font-mono">
                  {justification.length} chars
                </span>
              </div>
              <textarea
                rows={2}
                value={justification}
                onChange={(e) => {
                  setJustification(e.target.value);
                  if (errorMsg) setErrorMsg('');
                }}
                placeholder="Enter mandatory written justification for approving or rejecting this KYC case..."
                className={`w-full text-xs p-2.5 rounded-xl border bg-slate-50 dark:bg-[#202026] text-slate-900 dark:text-white outline-none focus:ring-2 transition-all ${
                  errorMsg
                    ? 'border-rose-500 focus:ring-rose-400'
                    : 'border-slate-300 dark:border-white/10 focus:ring-cyan-500'
                }`}
              />
              {errorMsg && (
                <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 mt-1">
                  {errorMsg}
                </p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <button
                type="button"
                onClick={() => onRequestCorrection(justification || 'Additional documents required')}
                disabled={loading}
                className="px-4 py-2 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 hover:bg-amber-200 border border-amber-300 dark:border-amber-800 transition-all shadow-xs"
              >
                Request Corrections
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleReject}
                  disabled={loading || !hasJustification || !isInReview}
                  className={`px-5 py-2 rounded-full text-xs font-bold transition-all shadow-sm ${
                    !hasJustification || !isInReview
                      ? 'bg-rose-200 dark:bg-zinc-800 text-slate-400 cursor-not-allowed opacity-60'
                      : 'bg-rose-600 hover:bg-rose-700 text-white active:scale-95'
                  }`}
                  title={!hasJustification ? 'Enter justification rationale to enable' : 'Reject Case'}
                >
                  {loading ? 'Processing...' : 'Reject Case'}
                </button>

                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={loading || !hasJustification || !isInReview}
                  className={`px-6 py-2 rounded-full text-xs font-bold transition-all shadow-sm ${
                    !hasJustification || !isInReview
                      ? 'bg-emerald-200 dark:bg-zinc-800 text-slate-400 cursor-not-allowed opacity-60'
                      : 'bg-emerald-600 hover:bg-emerald-700 text-white active:scale-95 shadow-emerald-500/20'
                  }`}
                  title={!hasJustification ? 'Enter justification rationale to enable' : 'Approve Case'}
                >
                  {loading ? 'Processing...' : 'Approve Case'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}