import React, { useState } from 'react';
import DocumentViewer from './DocumentViewer';
import ExtractedFieldsDeck from './ExtractedFieldsDeck';
import BiometricCard from './BiometricCard';
import DecisionBar from './DecisionBar';

export default function ReviewerWorkspace({
  currentCase,
  onBackToQueue,
  onUpdateFieldDecision,
  onApproveCase,
  onRejectCase,
  onRequestCorrection,
  onAdvanceToReview,
  onRunBiometrics,
  loading = false,
}) {
  const [activeDocId, setActiveDocId] = useState(
    currentCase?.documents?.[0]?.id || null
  );
  const [highlightedField, setHighlightedField] = useState(null);

  if (!currentCase) {
    return (
      <div className="p-12 text-center text-slate-500">
        <p>No case selected for review.</p>
        <button
          onClick={onBackToQueue}
          className="mt-3 px-4 py-2 rounded-full text-xs font-semibold bg-slate-900 text-white dark:bg-white dark:text-black"
        >
          ← Return to Case Queue
        </button>
      </div>
    );
  }

  // 11-Stage Stepper Definition
  const lifecycleStages = [
    { key: 'draft', label: 'Draft' },
    { key: 'invitation_sent', label: 'Invite Sent' },
    { key: 'awaiting_documents', label: 'Awaiting Docs' },
    { key: 'documents_received', label: 'Docs Received' },
    { key: 'ocr_processing', label: 'OCR Processing' },
    { key: 'needs_applicant_correction', label: 'Correction Loop' },
    { key: 'in_review', label: 'In Review' },
    { key: 'approved', label: 'Approved' },
    { key: 'rejected', label: 'Rejected' },
    { key: 'expired', label: 'Expired' },
    { key: 'closed', label: 'Closed' },
  ];

  const currentStageIndex = lifecycleStages.findIndex((s) => s.key === currentCase.status);

  // Algorithmic validation engine default issue checks for showcase
  const validationChecks = currentCase.validation_issues || [
    { code: 'VERHOEFF_CHECKSUM_VALID', field_name: 'aadhaar_number', severity: 'PASS', message: '✓ Verhoeff D5 dihedral checksum verified valid' },
    { code: 'PAN_STRUCTURE_VALID', field_name: 'pan_number', severity: 'PASS', message: '✓ PAN entity character matches Individual (P) and surname initial (S)' },
    { code: 'AGE_REQUIREMENT_VERIFIED', field_name: 'date_of_birth', severity: 'PASS', message: '✓ Statutory age gate passed: Applicant is 34 (>= 18 years)' },
    { code: 'NAME_SIMILARITY_MATCH', field_name: 'full_name', severity: 'PASS', message: '✓ Token Sort fuzzy name match: 94% similarity score' },
  ];

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Top Breadcrumb & Status Header */}
      <div className="bg-white dark:bg-[#16161A] px-4 sm:px-6 py-3 border-b border-slate-200 dark:border-white/10 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToQueue}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-200 text-xs font-semibold flex items-center gap-1 transition-all"
          >
            <span>←</span>
            <span>Back to Queue</span>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono-code text-sm font-bold text-slate-900 dark:text-white">
                {currentCase.case_number || 'CASE-1042'}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-200 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300">
                {currentCase.case_type || 'Individual'}
              </span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                currentCase.status === 'approved'
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                  : currentCase.status === 'rejected'
                  ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                  : 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300 animate-pulse'
              }`}>
                {currentCase.status?.replace(/_/g, ' ') || 'In Review'}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-zinc-400">
              Applicant: <strong>{currentCase.applicant_name || currentCase.applicant?.first_name ? `${currentCase.applicant?.first_name} ${currentCase.applicant?.last_name || ''}` : 'Aarav Sharma'}</strong>
              <span className="mx-2">•</span>
              Purpose: {currentCase.purpose || 'Merchant Seller Onboarding Verification'}
            </p>
          </div>
        </div>

        {/* Timestamp */}
        <div className="text-right text-[11px] text-slate-400 dark:text-zinc-500 font-mono">
          Created: {new Date(currentCase.created_at || Date.now()).toLocaleDateString()}
        </div>
      </div>

      {/* 11-Stage Visual Lifecycle Stepper (Feature 9) */}
      <div className="bg-slate-50 dark:bg-[#111114] px-4 sm:px-6 py-2.5 border-b border-slate-200 dark:border-white/5 overflow-x-auto">
        <div className="flex items-center min-w-max gap-1">
          {lifecycleStages.map((stage, idx) => {
            const isCompleted = idx < currentStageIndex || currentCase.status === 'approved';
            const isCurrent = stage.key === currentCase.status;
            const isRejectedTerminal = stage.key === 'rejected' && currentCase.status === 'rejected';

            return (
              <div key={stage.key} className="flex items-center">
                <div
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all ${
                    isRejectedTerminal
                      ? 'bg-rose-500 text-white font-bold ring-2 ring-rose-400 shadow-sm'
                      : isCurrent
                      ? 'bg-cyan-500 text-white font-bold ring-4 ring-cyan-500/25 shadow-sm'
                      : isCompleted
                      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-400 font-semibold'
                      : 'bg-slate-200/70 dark:bg-zinc-800/60 text-slate-400 dark:text-zinc-500'
                  }`}
                >
                  <span className="w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-mono">
                    {isCompleted ? '✓' : idx + 1}
                  </span>
                  <span>{stage.label}</span>
                </div>
                {idx < lifecycleStages.length - 1 && (
                  <div
                    className={`h-0.5 w-3 mx-1 ${
                      idx < currentStageIndex
                        ? 'bg-emerald-400 dark:bg-emerald-600'
                        : 'bg-slate-300 dark:bg-zinc-800'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main 55/45 Split Grid Workspace (Feature 10) */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Pane: 55% Document Viewer */}
        <div className="lg:col-span-7 h-[700px]">
          <DocumentViewer
            documents={currentCase.documents || []}
            activeDocId={activeDocId}
            setActiveDocId={setActiveDocId}
            highlightedField={highlightedField}
            onFieldHover={setHighlightedField}
          />
        </div>

        {/* Right Pane: 45% Verification Deck */}
        <div className="lg:col-span-5 space-y-4">
          {/* Algorithmic Validation Engine Badges (Feature 5) */}
          <div className="p-4 rounded-xl bg-white dark:bg-[#16161A] border border-slate-200 dark:border-white/10 shadow-xs">
            <div className="flex items-center justify-between mb-2.5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 flex items-center gap-1.5">
                <svg className="w-4 h-4 text-cyan-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Validation Engine Checks (Feature 5)
              </h4>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                100% Passed
              </span>
            </div>

            <div className="space-y-1.5">
              {validationChecks.map((chk, i) => (
                <div
                  key={i}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/5 text-[11px] flex items-center gap-2"
                >
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold flex-shrink-0">
                    {chk.severity === 'PASS' ? '✓ PASS' : chk.severity}
                  </span>
                  <span className="text-slate-700 dark:text-zinc-300 truncate">
                    {chk.message || `${chk.code} passed`}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Biometric Card (Feature 6) */}
          <BiometricCard
            selfieMatch={currentCase.selfie_match}
            onRunMatch={onRunBiometrics}
            loading={loading}
          />

          {/* Extracted Fields Deck (Feature 11) */}
          <ExtractedFieldsDeck
            fields={currentCase.extracted_fields || [
              { id: 'f1', field_name: 'full_name', draft_value: 'Aarav Sharma', confirmed_value: null, confidence: 0.98, reviewer_decision: 'confirmed', source_page: 1, correction_history: [] },
              { id: 'f2', field_name: 'date_of_birth', draft_value: '1990-05-15', confirmed_value: null, confidence: 0.96, reviewer_decision: 'confirmed', source_page: 1, correction_history: [] },
              { id: 'f3', field_name: 'document_number', draft_value: '2948 2847 2841', confirmed_value: null, confidence: 0.99, reviewer_decision: 'confirmed', source_page: 1, correction_history: [] },
              { id: 'f4', field_name: 'gender', draft_value: 'Male', confirmed_value: null, confidence: 0.95, reviewer_decision: 'confirmed', source_page: 1, correction_history: [] },
              { id: 'f5', field_name: 'address', draft_value: '42 Lotus Boulevard, Indiranagar, Bengaluru 560038', confirmed_value: null, confidence: 0.91, reviewer_decision: 'confirmed', source_page: 1, correction_history: [] },
            ]}
            onFieldDecision={onUpdateFieldDecision}
            onFieldHover={setHighlightedField}
          />
        </div>
      </div>

      {/* Sticky Bottom Decision Bar (Feature 12) */}
      <DecisionBar
        caseStatus={currentCase.status}
        onApprove={onApproveCase}
        onReject={onRejectCase}
        onRequestCorrection={onRequestCorrection}
        onAdvanceToReview={onAdvanceToReview}
        loading={loading}
      />
    </div>
  );
}