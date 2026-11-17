import React, { useState } from 'react';

export default function CredentialShowcase({
  isOpen,
  onClose,
  caseData,
  onRevokeShare,
}) {
  const [consentGranted, setConsentGranted] = useState(true);
  const [isRevoked, setIsRevoked] = useState(false);
  const [daysRemaining, setDaysRemaining] = useState(29);

  if (!isOpen) return null;

  const handleRevoke = () => {
    setIsRevoked(true);
    setConsentGranted(false);
    if (onRevokeShare) onRevokeShare();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="bg-white dark:bg-[#16161A] w-full max-w-xl rounded-3xl border border-slate-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Controlled Sharing & Digital Credential Showcase (Feature 15 & 16)
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Holographic Credential Card (design1.webp aesthetic) */}
          <div className="relative rounded-2xl overflow-hidden shadow-xl border border-white/40 dark:border-white/10 transition-transform hover:scale-[1.01]">
            {/* Iridescent Holographic Sheen Header */}
            <div
              className="p-6 text-slate-900 relative"
              style={{
                background:
                  'linear-gradient(135deg, #a7f3d0 0%, #bae6fd 50%, #fbcfe8 100%)',
              }}
            >
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-800 bg-white/70 px-2.5 py-0.5 rounded-full">
                    DIGITAL IDENTITY PASSPORT
                  </span>
                  <h2 className="text-xl font-black tracking-tight text-slate-950 mt-2">
                    VERIFIED KYC CREDENTIAL
                  </h2>
                  <p className="text-xs font-semibold text-slate-800">
                    Issuer: Apex Financial LLC (Verified Tenant)
                  </p>
                </div>

                {/* Cryptographic Seal */}
                <div className="w-14 h-14 rounded-full bg-white/80 backdrop-blur-xs border-2 border-slate-900 flex flex-col items-center justify-center text-center shadow-md">
                  <span className="text-[8px] font-black leading-none">SEALED</span>
                  <span className="text-xs font-black text-emerald-700">✓ SHA</span>
                  <span className="text-[7px] font-bold text-slate-600">ED25519</span>
                </div>
              </div>

              {/* 30-Day Countdown Badge */}
              <div className="mt-4 flex items-center justify-between bg-white/80 backdrop-blur-xs rounded-xl p-2.5 border border-white/60">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                  <span className="text-xs font-bold text-slate-900">
                    {isRevoked ? 'CREDENTIAL REVOKED' : `Valid for ${daysRemaining} more days (30-day grant)`}
                  </span>
                </div>
                <span className="font-mono text-[10px] font-bold bg-slate-900 text-white px-2 py-0.5 rounded-full">
                  {isRevoked ? '410 GONE' : 'EXPIRES IN 29d 14h'}
                </span>
              </div>
            </div>

            {/* Credential Body: Purpose-Bound Verified Claims */}
            <div className="p-6 bg-slate-900 text-white space-y-4">
              <div className="flex items-center justify-between text-xs border-b border-white/10 pb-2">
                <span className="text-zinc-400">Purpose Scope:</span>
                <span className="font-semibold text-cyan-300">Merchant Seller Onboarding</span>
              </div>

              {/* Claims Checklist */}
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Applicant Full Name:</span>
                  <span className="font-bold text-white">Aarav Sharma</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Date of Birth:</span>
                  <span className="font-mono text-zinc-200">1990-05-15 (Age: 34)</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Aadhaar Validation:</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <span>✓</span>
                    <span>Verhoeff Checksum Valid (Masked XXXX-XXXX-2841)</span>
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Biometric Match:</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <span>✓</span>
                    <span>92.4% Similarity Verified</span>
                  </span>
                </div>
              </div>

              {/* Privacy Seal Notice */}
              <div className="pt-2 border-t border-white/10 text-[11px] text-zinc-400 flex items-start gap-2">
                <svg className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span>
                  <strong>Zero-Knowledge Claim Isolation:</strong> Raw identity document binaries are strictly sealed in private storage. Recipient tenants receive only cryptographically verified claims.
                </span>
              </div>
            </div>
          </div>

          {/* Applicant Consent & Revocation Controls */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#202026] border border-slate-200 dark:border-white/5 space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <h4 className="text-xs font-bold text-slate-800 dark:text-zinc-200">
                  Applicant Consent & Revocation Authority
                </h4>
                <p className="text-[11px] text-slate-500 dark:text-zinc-400">
                  Applicants retain continuous control over their shared credentials.
                </p>
              </div>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                isRevoked
                  ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                  : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
              }`}>
                {isRevoked ? 'Consent Revoked' : 'Consent Active'}
              </span>
            </div>

            <div className="flex items-center gap-2 pt-1">
              {!isRevoked ? (
                <button
                  onClick={handleRevoke}
                  className="px-4 py-2 rounded-full text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-xs transition-all"
                >
                  Revoke Share Grant Immediately
                </button>
              ) : (
                <button
                  onClick={() => setIsRevoked(false)}
                  className="px-4 py-2 rounded-full text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-all"
                >
                  Re-grant Applicant Consent
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}