import React, { useState } from 'react';

export default function ExtractedFieldsDeck({
  fields = [],
  onFieldDecision,
  onFieldHover,
}) {
  const [editingFieldId, setEditingFieldId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [expandedHistoryId, setExpandedHistoryId] = useState(null);

  const startEdit = (field) => {
    setEditingFieldId(field.id);
    setEditValue(field.confirmed_value || field.draft_value || '');
    setReviewerNotes(field.reviewer_notes || '');
  };

  const cancelEdit = () => {
    setEditingFieldId(null);
    setEditValue('');
    setReviewerNotes('');
  };

  const submitEdit = (fieldId) => {
    if (!editValue.trim()) return;
    onFieldDecision(fieldId, 'corrected', editValue.trim(), reviewerNotes.trim());
    setEditingFieldId(null);
  };

  const handleConfirm = (field) => {
    onFieldDecision(field.id, 'confirmed', field.confirmed_value || field.draft_value);
  };

  const handleReject = (field) => {
    onFieldDecision(field.id, 'rejected', null, 'Rejected by reviewer');
  };

  const getConfidenceBadge = (confidence) => {
    const pct = Math.round((confidence || 0.9) * 100);
    if (pct >= 95) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800/50">
          High ({pct}%)
        </span>
      );
    }
    if (pct >= 70) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-300 dark:border-amber-800/50">
          Med ({pct}%)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-300 dark:border-rose-800/50">
        Low ({pct}%)
      </span>
    );
  };

  const getDecisionBadge = (decision) => {
    switch (decision) {
      case 'confirmed':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500 text-white shadow-xs">
            ✓ Confirmed
          </span>
        );
      case 'corrected':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500 text-white shadow-xs">
            ✎ Corrected
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500 text-white shadow-xs">
            ✗ Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
            • OCR Draft
          </span>
        );
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 flex items-center gap-1.5">
          <svg className="w-4 h-4 text-cyan-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Extracted KYC Fields ({fields.length})
        </h4>
        <span className="text-[11px] text-slate-400 dark:text-zinc-500">
          Inline Reviewer Gates
        </span>
      </div>

      <div className="space-y-2.5">
        {fields.map((field) => {
          const isEditing = editingFieldId === field.id;
          const hasHistory = field.correction_history && field.correction_history.length > 0;
          const isHistoryExpanded = expandedHistoryId === field.id;

          return (
            <div
              key={field.id}
              onMouseEnter={() => onFieldHover && onFieldHover(field.field_name)}
              onMouseLeave={() => onFieldHover && onFieldHover(null)}
              className="p-3.5 rounded-xl bg-white dark:bg-[#16161A] border border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/20 transition-all shadow-xs"
            >
              {/* Card Header: Label & Badges */}
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-zinc-300">
                    {field.field_name.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[10px] text-slate-400 dark:text-zinc-500 font-mono">
                    Page {field.source_page || 1}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  {getConfidenceBadge(field.confidence)}
                  {getDecisionBadge(field.reviewer_decision)}
                </div>
              </div>

              {/* Card Body: Values */}
              {isEditing ? (
                <div className="space-y-2 mt-2 pt-2 border-t border-slate-100 dark:border-white/5">
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400 dark:text-zinc-500 block mb-1">
                      Corrected Value:
                    </label>
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-full text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-cyan-400 dark:border-cyan-600 bg-cyan-50/30 dark:bg-zinc-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-cyan-500"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder="Optional reviewer notes / reason for edit..."
                      value={reviewerNotes}
                      onChange={(e) => setReviewerNotes(e.target.value)}
                      className="w-full text-[11px] px-2.5 py-1 rounded border border-slate-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-slate-800 dark:text-zinc-300 outline-none"
                    />
                  </div>
                  <div className="flex items-center justify-end gap-1.5 pt-1">
                    <button
                      onClick={cancelEdit}
                      className="px-2.5 py-1 rounded text-xs font-medium bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 hover:bg-slate-200"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => submitEdit(field.id)}
                      className="px-3 py-1 rounded text-xs font-semibold bg-cyan-600 hover:bg-cyan-700 text-white shadow-xs"
                    >
                      Save Correction
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex items-baseline justify-between gap-3">
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-slate-900 dark:text-white">
                        {field.confirmed_value ? (
                          <div className="flex items-center gap-2">
                            <span>{field.confirmed_value}</span>
                            <span className="text-[10px] text-cyan-600 dark:text-cyan-400 font-normal">
                              (Edited from "{field.draft_value}")
                            </span>
                          </div>
                        ) : (
                          <span>{field.draft_value || '—'}</span>
                        )}
                      </div>
                    </div>

                    {/* Inline Action Triggers */}
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={() => handleConfirm(field)}
                        title="Confirm draft value"
                        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
                          field.reviewer_decision === 'confirmed'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-bold'
                            : 'bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 hover:text-emerald-700'
                        }`}
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => startEdit(field)}
                        title="Edit or correct field value"
                        className="px-2 py-1 rounded text-xs font-medium bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 hover:text-cyan-700 transition-all"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleReject(field)}
                        title="Reject field"
                        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
                          field.reviewer_decision === 'rejected'
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 font-bold'
                            : 'bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 hover:bg-rose-50 dark:hover:bg-rose-950/40 hover:text-rose-700'
                        }`}
                      >
                        Reject
                      </button>
                    </div>
                  </div>

                  {/* Correction History Drawer / Indicator */}
                  {hasHistory && (
                    <div className="mt-2 pt-1.5 border-t border-slate-100 dark:border-white/5">
                      <button
                        onClick={() => setExpandedHistoryId(isHistoryExpanded ? null : field.id)}
                        className="text-[10px] text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 font-medium"
                      >
                        <span>Audit Trail ({field.correction_history.length} corrections)</span>
                        <span>{isHistoryExpanded ? '▲' : '▼'}</span>
                      </button>

                      {isHistoryExpanded && (
                        <div className="mt-1.5 pl-2 border-l-2 border-cyan-400 space-y-1">
                          {field.correction_history.map((hist, idx) => (
                            <div key={idx} className="text-[10px] text-slate-600 dark:text-zinc-400">
                              <span className="font-semibold text-slate-700 dark:text-zinc-300">"{hist.from_value}"</span>
                              <span className="mx-1">→</span>
                              <span className="font-semibold text-emerald-600 dark:text-emerald-400">"{hist.to_value}"</span>
                              <span className="text-slate-400 dark:text-zinc-500 ml-1.5">
                                by {hist.reviewer_id || 'Reviewer'} ({new Date(hist.timestamp || Date.now()).toLocaleTimeString()})
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}