import React, { useState } from 'react';

export default function CaseList({
  cases = [],
  onSelectCase,
  onOpenNewCaseModal,
  loading = false,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('newest');

  // Compute KPI metrics
  const totalOpen = cases.filter((c) => !['approved', 'rejected', 'closed', 'expired'].includes(c.status)).length;
  const pendingReview = cases.filter((c) => ['in_review', 'documents_received', 'ocr_processing'].includes(c.status)).length;
  const completed = cases.filter((c) => c.status === 'approved').length;
  const expiringShares = 14; // Showcase metric

  // Filter & Search Logic
  const filteredCases = cases.filter((item) => {
    const matchesSearch =
      (item.case_number && item.case_number.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.applicant_name && item.applicant_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.purpose && item.purpose.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus =
      statusFilter === 'ALL' || item.status?.toUpperCase() === statusFilter.toUpperCase();

    const matchesType =
      typeFilter === 'ALL' || item.case_type?.toUpperCase() === typeFilter.toUpperCase();

    return matchesSearch && matchesStatus && matchesType;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* 4 KPI Summary Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="p-4 rounded-xl bg-white dark:bg-[#16161A] border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-zinc-500 block">
              Open Cases
            </span>
            <div className="text-2xl font-black text-slate-900 dark:text-white mt-1">
              {totalOpen}
            </div>
            <span className="inline-flex items-center text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
              ↑ 12% this week
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-cyan-100 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 flex items-center justify-center font-bold">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="p-4 rounded-xl bg-white dark:bg-[#16161A] border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-zinc-500 block">
              Pending OCR Review
            </span>
            <div className="text-2xl font-black text-slate-900 dark:text-white mt-1">
              {pendingReview}
            </div>
            <span className="inline-flex items-center text-[10px] font-semibold text-amber-600 dark:text-amber-400 mt-1">
              • High Review Priority
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 flex items-center justify-center font-bold">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="p-4 rounded-xl bg-white dark:bg-[#16161A] border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-zinc-500 block">
              Active Share Grants
            </span>
            <div className="text-2xl font-black text-slate-900 dark:text-white mt-1">
              {expiringShares}
            </div>
            <span className="inline-flex items-center text-[10px] font-semibold text-cyan-600 dark:text-cyan-400 mt-1">
              30-day countdown timer
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="p-4 rounded-xl bg-white dark:bg-[#16161A] border border-slate-200 dark:border-white/10 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-zinc-500 block">
              Completed Onboardings
            </span>
            <div className="text-2xl font-black text-slate-900 dark:text-white mt-1">
              {completed}
            </div>
            <span className="inline-flex items-center text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
              100% Verification Rate
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 flex items-center justify-center font-bold">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="bg-white dark:bg-[#16161A] p-4 rounded-xl border border-slate-200 dark:border-white/10 shadow-xs flex flex-wrap items-center justify-between gap-3">
        {/* Search bar */}
        <div className="relative flex-1 min-w-[240px]">
          <svg className="w-4 h-4 absolute left-3 top-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by Case ID, applicant name, purpose..."
            className="w-full text-xs pl-9 pr-4 py-2 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>

        {/* Status Filter Buttons */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
          {['ALL', 'IN_REVIEW', 'DOCUMENTS_RECEIVED', 'APPROVED', 'REJECTED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                statusFilter === st
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-black shadow-xs'
                  : 'bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 hover:bg-slate-200'
              }`}
            >
              {st === 'ALL' ? 'All Status' : st.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        {/* Case Type Filter */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/10 text-slate-800 dark:text-zinc-200 outline-none"
        >
          <option value="ALL">All Types</option>
          <option value="INDIVIDUAL">Individual</option>
          <option value="BUSINESS">Business</option>
        </select>
      </div>

      {/* Case Data Grid Table */}
      <div className="bg-white dark:bg-[#16161A] rounded-xl border border-slate-200 dark:border-white/10 shadow-xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-white/10 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-zinc-400">
            Active KYC Verification Queue ({filteredCases.length})
          </h3>
          <span className="text-[11px] text-slate-400 font-mono">
            Auto-refresh active
          </span>
        </div>

        {filteredCases.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-[#202026] text-slate-500 dark:text-zinc-400 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200 dark:border-white/5">
                <tr>
                  <th className="px-5 py-3">Case ID</th>
                  <th className="px-5 py-3">Applicant / Entity</th>
                  <th className="px-5 py-3">Verification Purpose</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Documents</th>
                  <th className="px-5 py-3">Submitted</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/5 text-slate-700 dark:text-zinc-300">
                {filteredCases.map((item) => {
                  const isApproved = item.status === 'approved';
                  const isRejected = item.status === 'rejected';
                  const isInReview = item.status === 'in_review';

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-[#202026]/50 transition-colors"
                    >
                      <td className="px-5 py-4 font-mono-code font-bold text-slate-900 dark:text-white">
                        {item.case_number}
                      </td>
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {item.applicant_name || 'Aarav Sharma'}
                        </div>
                        <span className="inline-block mt-0.5 px-2 py-0.2 rounded-full text-[9px] font-bold uppercase tracking-wider bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400">
                          {item.case_type || 'Individual'}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-slate-600 dark:text-zinc-300 max-w-xs truncate">
                        {item.purpose || 'Merchant Verification'}
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${
                            isApproved
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-400'
                              : isRejected
                              ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/70 dark:text-rose-400'
                              : isInReview
                              ? 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950/70 dark:text-cyan-300'
                              : 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-400'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isApproved
                                ? 'bg-emerald-500'
                                : isRejected
                                ? 'bg-rose-500'
                                : 'bg-cyan-500 animate-ping'
                            }`}
                          />
                          {item.status?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-slate-600 dark:text-zinc-400 font-medium">
                        {item.document_count || 1} doc(s)
                      </td>
                      <td className="px-5 py-4 text-slate-500 dark:text-zinc-400 font-mono text-[11px]">
                        {new Date(item.created_at || Date.now()).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={() => onSelectCase(item)}
                          className="px-3.5 py-1.5 rounded-full text-xs font-semibold bg-slate-900 text-white dark:bg-white dark:text-black hover:bg-slate-800 dark:hover:bg-neutral-200 transition-all shadow-xs"
                        >
                          Inspect / Review →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-400 dark:text-zinc-500 space-y-3">
            <svg className="w-12 h-12 mx-auto opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="font-semibold text-sm">No KYC cases match your filter criteria.</p>
            <button
              onClick={onOpenNewCaseModal}
              className="px-4 py-2 rounded-full text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm"
            >
              + Create New KYC Case
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
