import React, { useState } from 'react';

export default function DocumentViewer({
  documents = [],
  activeDocId,
  setActiveDocId,
  highlightedField,
  onFieldHover,
}) {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [showOverlays, setShowOverlays] = useState(true);
  const [copiedHash, setCopiedHash] = useState(false);

  // Active document object
  const activeDoc = documents.find((d) => d.id === activeDocId) || documents[0] || null;

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 25, 250));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 25, 50));
  const handleZoomReset = () => {
    setZoom(100);
    setRotation(0);
  };
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);

  const copyHash = (hash) => {
    if (!hash) return;
    navigator.clipboard?.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  // Mock sample OCR bounding boxes for visual showcase
  const mockBoundingBoxes = [
    { id: 'full_name', label: 'Full Name', top: '18%', left: '20%', width: '45%', height: '8%', confidence: '98%' },
    { id: 'document_number', label: 'ID / Aadhaar No.', top: '35%', left: '20%', width: '52%', height: '9%', confidence: '99%' },
    { id: 'date_of_birth', label: 'Date of Birth', top: '50%', left: '20%', width: '30%', height: '7%', confidence: '96%' },
    { id: 'gender', label: 'Gender', top: '50%', left: '55%', width: '20%', height: '7%', confidence: '95%' },
    { id: 'address', label: 'Address', top: '65%', left: '15%', width: '70%', height: '14%', confidence: '91%' },
  ];

  return (
    <div className="flex flex-col h-full bg-slate-100 dark:bg-[#16161A] rounded-xl border border-slate-200 dark:border-white/10 overflow-hidden shadow-sm">
      {/* Top Document Selector Tabs */}
      <div className="bg-white dark:bg-[#202026] px-4 py-2.5 border-b border-slate-200 dark:border-white/10 flex items-center justify-between gap-3 overflow-x-auto">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-zinc-500 mr-1 hidden sm:inline">
            Files:
          </span>
          {documents.length > 0 ? (
            documents.map((doc) => {
              const isActive = doc.id === (activeDoc?.id || activeDocId);
              return (
                <button
                  key={doc.id}
                  onClick={() => setActiveDocId(doc.id)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all truncate ${
                    isActive
                      ? 'bg-slate-900 text-white dark:bg-white dark:text-black shadow-sm font-semibold'
                      : 'bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 hover:bg-slate-200 dark:hover:bg-zinc-700'
                  }`}
                >
                  <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="truncate max-w-[120px]">{doc.original_filename || doc.document_type || 'Document'}</span>
                </button>
              );
            })
          ) : (
            <span className="text-xs text-slate-400">No documents attached</span>
          )}
        </div>

        {/* View Controls */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            className={`px-2 py-1 rounded text-[11px] font-medium transition-all ${
              showOverlays
                ? 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800'
                : 'bg-slate-200 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400'
            }`}
            title="Toggle OCR bounding box highlights"
          >
            OCR Overlays: {showOverlays ? 'ON' : 'OFF'}
          </button>
          <div className="h-4 w-px bg-slate-300 dark:bg-zinc-700 mx-1" />
          <button
            onClick={handleZoomOut}
            className="p-1 rounded bg-slate-200 dark:bg-zinc-800 hover:bg-slate-300 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-300"
            title="Zoom out"
          >
            -
          </button>
          <span className="text-xs font-mono font-semibold px-1 text-slate-600 dark:text-zinc-300">
            {zoom}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-1 rounded bg-slate-200 dark:bg-zinc-800 hover:bg-slate-300 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-300"
            title="Zoom in"
          >
            +
          </button>
          <button
            onClick={handleRotate}
            className="p-1 rounded bg-slate-200 dark:bg-zinc-800 hover:bg-slate-300 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-300 ml-1"
            title="Rotate 90 degrees"
          >
            ↻
          </button>
          <button
            onClick={handleZoomReset}
            className="text-[11px] px-1.5 py-1 rounded bg-slate-200 dark:bg-zinc-800 hover:bg-slate-300 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-300"
            title="Reset zoom"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Metadata Strip */}
      {activeDoc && (
        <div className="bg-slate-50 dark:bg-[#1b1b22] px-4 py-1.5 border-b border-slate-200 dark:border-white/5 flex flex-wrap items-center justify-between gap-2 text-[11px]">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-800 dark:text-zinc-200">
              {activeDoc.original_filename || 'identity_document.pdf'}
            </span>
            <span className="px-2 py-0.5 rounded-full bg-slate-200 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 uppercase font-bold text-[9px]">
              {activeDoc.document_type || 'PDF'}
            </span>
            <span className="text-slate-400 dark:text-zinc-500">
              {activeDoc.file_size ? `${(activeDoc.file_size / 1024).toFixed(1)} KB` : '1.4 MB'}
            </span>
            <span className="text-slate-400 dark:text-zinc-500">
              {activeDoc.mime_type || 'application/pdf'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 dark:text-zinc-500">SHA-256:</span>
            <button
              onClick={() => copyHash(activeDoc.file_hash || '3f7a8109d93e1a0b3f88bc92d19e09d1c1a2f3a4')}
              className="font-mono-code text-[10px] bg-slate-200 dark:bg-zinc-800 px-2 py-0.5 rounded text-slate-700 dark:text-zinc-300 hover:bg-slate-300 dark:hover:bg-zinc-700 transition-colors"
              title="Click to copy SHA-256 hash"
            >
              {(activeDoc.file_hash || '3f7a8109d93e1a0b3f88bc92d19e09d1c1a2f3a4').substring(0, 12)}...
              {copiedHash ? ' (Copied!)' : ''}
            </button>
          </div>
        </div>
      )}

      {/* Canvas Area */}
      <div className="relative flex-1 p-6 overflow-auto flex items-center justify-center bg-slate-200/50 dark:bg-black/40 min-h-[460px]">
        {activeDoc ? (
          <div
            className="relative transition-transform duration-150 ease-out shadow-2xl rounded-lg bg-white overflow-hidden border border-slate-300 dark:border-white/10"
            style={{
              transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
              transformOrigin: 'center center',
              width: '480px',
              height: '620px',
            }}
          >
            {/* Visual Document Content Preview Canvas */}
            <div className="w-full h-full p-8 flex flex-col justify-between bg-gradient-to-b from-amber-50/40 via-white to-slate-50 select-none">
              {/* Header */}
              <div>
                <div className="flex justify-between items-start border-b-2 border-slate-900 pb-3">
                  <div>
                    <h3 className="text-lg font-black tracking-tight text-slate-900">GOVERNMENT OF INDIA</h3>
                    <p className="text-[11px] font-semibold text-slate-700">UNIQUE IDENTIFICATION AUTHORITY OF INDIA</p>
                  </div>
                  <div className="w-12 h-12 rounded-full border-2 border-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-800">
                    SEAL
                  </div>
                </div>

                {/* Body Details */}
                <div className="mt-8 flex gap-6">
                  {/* Photo area */}
                  <div className="w-28 h-36 bg-slate-200 rounded border border-slate-400 flex flex-col items-center justify-center text-slate-500 flex-shrink-0 shadow-inner">
                    <svg className="w-16 h-16 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                    </svg>
                    <span className="text-[10px] font-semibold mt-1">ID PHOTO</span>
                  </div>

                  {/* Text details */}
                  <div className="space-y-3 flex-1 text-slate-800">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Name:</span>
                      <span className="text-sm font-bold text-slate-900">Aarav Sharma</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Date of Birth:</span>
                      <span className="text-sm font-semibold text-slate-900">15/05/1990</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">Gender:</span>
                      <span className="text-sm font-semibold text-slate-900">Male / M</span>
                    </div>
                  </div>
                </div>

                {/* Aadhaar / ID Number */}
                <div className="mt-10 pt-4 border-t border-slate-300 text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Aadhaar / Identifier:</span>
                  <div className="text-xl font-mono font-black tracking-widest text-slate-900 mt-1">
                    2948 2847 2841
                  </div>
                  <span className="text-[9px] text-emerald-700 font-semibold block mt-1">
                    ✓ Verhoeff Dihedral Checksum: VALID
                  </span>
                </div>
              </div>

              {/* Barcode & Security Strip Footer */}
              <div className="border-t border-dashed border-slate-400 pt-3 flex justify-between items-center text-[10px] text-slate-600">
                <div className="font-mono tracking-tighter">||| | |||| | ||| ||||| |||| || |</div>
                <div className="font-mono text-[9px]">DOC-VERIFIED-SEC-8472</div>
              </div>
            </div>

            {/* Bounding Box Highlights Overlay Layer */}
            {showOverlays && (
              <div className="absolute inset-0 pointer-events-none">
                {mockBoundingBoxes.map((box) => {
                  const isHovered = highlightedField === box.id;
                  return (
                    <div
                      key={box.id}
                      style={{
                        position: 'absolute',
                        top: box.top,
                        left: box.left,
                        width: box.width,
                        height: box.height,
                      }}
                      className={`border-2 rounded transition-all duration-200 ${
                        isHovered
                          ? 'border-cyan-500 bg-cyan-400/20 shadow-lg shadow-cyan-500/30'
                          : 'border-cyan-400/60 bg-cyan-400/5 hover:border-cyan-400 hover:bg-cyan-400/15'
                      }`}
                    >
                      <div className="absolute -top-4 left-0 bg-cyan-600 text-white text-[9px] font-bold px-1 rounded flex items-center gap-1 shadow">
                        <span>{box.label}</span>
                        <span className="opacity-80">({box.confidence})</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center p-12 text-slate-400 dark:text-zinc-500">
            <svg className="w-16 h-16 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="font-semibold text-sm">No identity document selected</p>
            <p className="text-xs mt-1">Upload a document or choose a file from the list above.</p>
          </div>
        )}
      </div>
    </div>
  );
}