import React, { useState } from 'react';

export default function EmailSimulatorModal({
  isOpen,
  onClose,
  activeCases = [],
  onIngestWebhook,
  onIngestEml,
  onAssignException,
  onDismissException,
  exceptions = [],
  loading = false,
}) {
  const [activeTab, setActiveTab] = useState('webhook');

  // Webhook State
  const [sender, setSender] = useState('aarav.sharma@example.com');
  const [subject, setSubject] = useState('KYC Document Submission [CASE-1042]');
  const [bodyText, setBodyText] = useState('Please find attached my Aadhaar and PAN documents for verification.');
  const [webhookResult, setWebhookResult] = useState(null);

  // EML Presets State
  const [selectedPreset, setSelectedPreset] = useState('matched');
  const [emlResult, setEmlResult] = useState(null);

  // Exception assignment state
  const [selectedCaseForAssign, setSelectedCaseForAssign] = useState({});

  if (!isOpen) return null;

  const handleWebhookSubmit = async (e) => {
    e.preventDefault();
    const result = await onIngestWebhook({
      sender,
      subject,
      bodyText,
    });
    setWebhookResult(result);
  };

  const handleEmlPresetSubmit = async (preset) => {
    const result = await onIngestEml(preset);
    setEmlResult(result);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div className="bg-white dark:bg-[#16161A] w-full max-w-2xl rounded-2xl border border-slate-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-white/10 flex items-center justify-between bg-slate-50 dark:bg-[#202026]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-sm">
              ✉
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Email Intake Simulator & Exception Triage
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-zinc-400">
                Test inbound document ingestion via REST Webhook or RFC 822 .eml
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-zinc-800"
          >
            ✕
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 dark:border-white/10 bg-slate-100/50 dark:bg-[#111114] px-6 gap-2">
          <button
            onClick={() => setActiveTab('webhook')}
            className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'webhook'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-white'
            }`}
          >
            REST Webhook Ingestion
          </button>
          <button
            onClick={() => setActiveTab('eml')}
            className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === 'eml'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-white'
            }`}
          >
            RFC 822 .EML Stream
          </button>
          <button
            onClick={() => setActiveTab('exceptions')}
            className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'exceptions'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-white'
            }`}
          >
            <span>Exception Queue</span>
            {exceptions.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500 text-white font-bold">
                {exceptions.length}
              </span>
            )}
          </button>
        </div>

        {/* Tab Contents */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {/* TAB 1: WEBHOOK */}
          {activeTab === 'webhook' && (
            <form onSubmit={handleWebhookSubmit} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300 block mb-1">
                  Applicant Sender Email:
                </label>
                <input
                  type="email"
                  value={sender}
                  onChange={(e) => setSender(e.target.value)}
                  required
                  className="w-full text-xs px-3 py-2 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300 block mb-1">
                  Subject Line (Include [CASE-XXXX] to auto-match):
                </label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  required
                  className="w-full text-xs px-3 py-2 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                />
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Omitting the case token routes the email directly to the Exception Queue.
                </span>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300 block mb-1">
                  Body Text:
                </label>
                <textarea
                  rows={2}
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-700 dark:text-zinc-300">
                    Synthetic Document:
                  </span>
                  <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400">
                    aadhaar_synthetic_scan.pdf (1.2 MB)
                  </span>
                </div>
                <span className="text-[10px] bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 px-2 py-0.5 rounded-full font-bold">
                  Magic Bytes: %PDF-1.4
                </span>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-full text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-all"
              >
                {loading ? 'Ingesting...' : 'Trigger Webhook Document Intake →'}
              </button>

              {webhookResult && (
                <div className="p-3 rounded-lg bg-slate-900 text-slate-100 text-xs font-mono space-y-1">
                  <div className="text-emerald-400 font-bold">✓ Intake Ingestion Response:</div>
                  <div>Status: {webhookResult.status}</div>
                  <div>Case ID: {webhookResult.case_id || 'Routed to Exception Queue'}</div>
                  <div>Message ID: {webhookResult.message_id}</div>
                </div>
              )}
            </form>
          )}

          {/* TAB 2: EML SIMULATOR */}
          {activeTab === 'eml' && (
            <div className="space-y-4">
              <p className="text-xs text-slate-600 dark:text-zinc-300">
                Choose a synthetic RFC 822 email preset or test edge case deduplication:
              </p>

              <div className="space-y-2">
                <div
                  onClick={() => setSelectedPreset('matched')}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedPreset === 'matched'
                      ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/30'
                      : 'border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-[#202026]'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-slate-900 dark:text-white">
                      Preset 1: Matched Subject Token [CASE-1042]
                    </span>
                    <span className="text-[10px] bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 px-2 py-0.5 rounded-full font-bold">
                      Auto-Attach
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1">
                    Contains 2 attachments (PDF & JPEG). Advances case status to <code>documents_received</code>.
                  </p>
                </div>

                <div
                  onClick={() => setSelectedPreset('unmatched')}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedPreset === 'unmatched'
                      ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/30'
                      : 'border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-[#202026]'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-slate-900 dark:text-white">
                      Preset 2: Unmatched Subject Token
                    </span>
                    <span className="text-[10px] bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 px-2 py-0.5 rounded-full font-bold">
                      Exception Queue
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1">
                    No recognized case ID. Enqueues message into the Email Exception Queue for manual reviewer assignment.
                  </p>
                </div>

                <div
                  onClick={() => setSelectedPreset('duplicate')}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedPreset === 'duplicate'
                      ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/30'
                      : 'border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-[#202026]'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-slate-900 dark:text-white">
                      Preset 3: Idempotent Duplicate Message-ID
                    </span>
                    <span className="text-[10px] bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300 px-2 py-0.5 rounded-full font-bold">
                      Deduplication
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1">
                    Submits identical <code>Message-ID</code>; returns HTTP 200 with <code>idempotent_duplicate</code> without creating duplicate database rows.
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleEmlPresetSubmit(selectedPreset)}
                disabled={loading}
                className="w-full py-2.5 rounded-full text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-all"
              >
                {loading ? 'Ingesting...' : 'Ingest .EML Binary Stream →'}
              </button>

              {emlResult && (
                <div className="p-3 rounded-lg bg-slate-900 text-slate-100 text-xs font-mono space-y-1">
                  <div className="text-emerald-400 font-bold">✓ EML Ingestion Response:</div>
                  <div>Status: {emlResult.status}</div>
                  <div>Attachments Parsed: {emlResult.attachments_count || 2}</div>
                  <div>Target Case: {emlResult.case_number || 'Routed to Exception Queue'}</div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: EXCEPTION QUEUE */}
          {activeTab === 'exceptions' && (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs font-semibold text-slate-700 dark:text-zinc-300">
                  Unmatched Inbound Emails Awaiting Manual Assignment:
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  {exceptions.length} items
                </span>
              </div>

              {exceptions.length > 0 ? (
                <div className="space-y-2.5">
                  {exceptions.map((exc) => (
                    <div
                      key={exc.id}
                      className="p-3 rounded-xl bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/10 space-y-2"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="text-xs font-bold text-slate-900 dark:text-white">
                            {exc.subject || 'Unmatched Subject'}
                          </div>
                          <div className="text-[11px] text-slate-500 dark:text-zinc-400">
                            From: {exc.sender} • {exc.attachments_count || 1} attachment(s)
                          </div>
                        </div>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 uppercase">
                          {exc.status}
                        </span>
                      </div>

                      {/* Assignment Controls */}
                      <div className="flex items-center gap-2 pt-1 border-t border-slate-200 dark:border-white/5">
                        <select
                          value={selectedCaseForAssign[exc.id] || ''}
                          onChange={(e) =>
                            setSelectedCaseForAssign({
                              ...selectedCaseForAssign,
                              [exc.id]: e.target.value,
                            })
                          }
                          className="flex-1 text-xs px-2.5 py-1 rounded bg-white dark:bg-zinc-800 border border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-white outline-none"
                        >
                          <option value="">Select target KYC Case...</option>
                          {activeCases
                            .filter((c) => !['approved', 'rejected', 'closed', 'expired'].includes(c.status))
                            .map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.case_number} - {c.applicant_name || 'Aarav Sharma'} ({c.status})
                              </option>
                            ))}
                        </select>

                        <button
                          onClick={() => {
                            const caseId = selectedCaseForAssign[exc.id];
                            if (caseId) onAssignException(exc.id, caseId);
                          }}
                          disabled={!selectedCaseForAssign[exc.id]}
                          className="px-3 py-1 rounded text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-40"
                        >
                          Assign →
                        </button>

                        <button
                          onClick={() => onDismissException(exc.id)}
                          className="px-2.5 py-1 rounded text-xs font-medium bg-slate-200 dark:bg-zinc-800 hover:bg-rose-100 text-slate-600 dark:text-zinc-400 hover:text-rose-700"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-400 dark:text-zinc-500 text-xs">
                  ✓ Email Exception Queue is clear. No unmatched messages pending triage.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
