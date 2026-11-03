import React, { useState, useEffect, useCallback } from 'react'
import {
  X, Download, Calendar, TrendingUp, FileText,
  ImageOff, ZoomIn, CheckCircle, AlertTriangle,
  Flame, Eye, SplitSquareVertical, Sparkles
} from 'lucide-react'

import { API_BASE_URL, getFullImageUrl } from '../services/api'

/** Confidence colour helpers */
function confidenceColor(pct) {
  if (pct >= 90) return { text: 'text-emerald-400', bar: 'from-emerald-500 to-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' }
  if (pct >= 75) return { text: 'text-yellow-400',  bar: 'from-yellow-500 to-yellow-400',  bg: 'bg-yellow-500/10 border-yellow-500/20'  }
  return          { text: 'text-red-400',    bar: 'from-red-500 to-red-400',    bg: 'bg-red-500/10 border-red-500/20'    }
}

function diseaseBadgeClass(disease) {
  const d = (disease || '').toLowerCase()
  if (d.includes('pneumonia'))   return 'bg-red-500/15 text-red-300 border-red-500/25'
  if (d.includes('cardio'))      return 'bg-orange-500/15 text-orange-300 border-orange-500/25'
  if (d.includes('effusion'))    return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/25'
  if (d.includes('atelectasis')) return 'bg-purple-500/15 text-purple-300 border-purple-500/25'
  if (d.includes('no finding'))  return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25'
  return 'bg-clinical-500/15 text-clinical-300 border-clinical-500/25'
}

/**
 * ReportModal — full-detail overlay for a single X-ray report with Grad-CAM support.
 *
 * Props:
 *   report  — the report object from /reports API
 *   onClose — callback to clear selectedReport
 */
function ReportModal({ report, onClose }) {
  const [imgError,     setImgError]     = useState(false)
  const [heatmapError, setHeatmapError] = useState(false)
  const [zoomed,       setZoomed]       = useState(false)
  const [pdfLoading,   setPdfLoading]   = useState(false)

  const pct    = Math.round((report.confidence || 0) * 100)
  const colors = confidenceColor(pct)

  const date = new Date(report.created_at)
  const dateStr = date.toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' })
  const timeStr = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

  // Fully qualified URLs
  const imageUrl = getFullImageUrl(report.image_url || report.image_path)
  const heatmapUrl = report.heatmap_url
    ? getFullImageUrl(report.heatmap_url)
    : (report.heatmap_path ? getFullImageUrl(report.heatmap_path) : '')

  const [activeTab, setActiveTab] = useState(heatmapUrl ? 'heatmap' : 'original')

  /* ── Close on Escape key ─────────────────────────────────── */
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [handleKeyDown])

  /* ── PDF download (browser print-to-PDF) ─────────────────── */
  const handleDownloadPDF = () => {
    setPdfLoading(true)
    const win = window.open('', '_blank')
    const content = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>X-ray Report #${report.id} — ${report.disease}</title>
        <style>
          body { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; max-width: 750px; margin: 40px auto; color: #1e293b; line-height: 1.5; }
          h1   { font-size: 24px; margin-bottom: 4px; color: #0f172a; }
          .meta{ color: #64748b; font-size: 13px; margin-bottom: 20px; }
          .badge { display:inline-block; padding:4px 14px; border-radius:999px; background:#eff6ff; color:#1d4ed8; font-weight:700; font-size:13px; margin-bottom:16px; border:1px solid #bfdbfe; }
          .conf-wrap { margin-bottom: 24px; }
          .conf { font-size: 28px; font-weight: 800; color: #0f766e; }
          .bar-wrap { background:#e2e8f0; border-radius:8px; height:8px; margin:8px 0; }
          .bar { background: linear-gradient(90deg,#0d9488,#2563eb); height:8px; border-radius:8px; width:${pct}%; }
          .images-grid { display: flex; gap: 16px; margin: 24px 0; }
          .img-card { flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; text-align: center; }
          .img-card img { max-width: 100%; max-height: 280px; object-fit: contain; border-radius: 8px; }
          .img-label { font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-top: 8px; }
          pre  { white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 13px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:20px; line-height:1.7; color: #334155; }
          .xai-note { background: #fef3c7; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #92400e; margin: 16px 0; }
          .footer { margin-top:36px; font-size:11px; color:#94a3b8; border-top:1px solid #e2e8f0; padding-top:16px; }
        </style>
      </head>
      <body>
        <h1>Clinical Radiology Report & AI Interpretability</h1>
        <div class="meta">Report #${report.id} &nbsp;·&nbsp; ${dateStr} at ${timeStr}</div>
        <div class="badge">${report.disease}</div>

        <div class="conf-wrap">
          <p style="margin:0;font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;">AI Model Confidence</p>
          <div class="conf">${pct}%</div>
          <div class="bar-wrap"><div class="bar"></div></div>
        </div>

        ${heatmapUrl ? `
          <div class="xai-note">
            <strong>Explainable AI Visual Saliency (Grad-CAM):</strong>
            Thermal colormap highlights discriminative pulmonary regions derived from EfficientNetB0 (<code>top_conv</code> layer) indicating <strong>${report.disease}</strong>.
          </div>
          <div class="images-grid">
            <div class="img-card">
              <img src="${imageUrl}" alt="Source X-ray" />
              <div class="img-label">Figure 1: Source Radiograph</div>
            </div>
            <div class="img-card">
              <img src="${heatmapUrl}" alt="Grad-CAM Heatmap" />
              <div class="img-label" style="color:#b91c1c;">Figure 2: Grad-CAM Activation Heatmap</div>
            </div>
          </div>
        ` : `
          <div class="images-grid">
            <div class="img-card" style="flex:none;max-width:320px;">
              <img src="${imageUrl}" alt="Source X-ray" />
              <div class="img-label">Figure 1: Source Radiograph</div>
            </div>
          </div>
        `}

        <p style="margin:20px 0 6px;font-weight:700;font-size:14px;">Full Radiology Findings & Clinical Impression</p>
        <pre>${report.report_text || 'Report text not available for this entry.'}</pre>

        <div class="footer">
          ⚠ This is an AI-generated decision support draft. A licensed radiologist must review and sign off before any clinical decision is made.<br/>
          Architecture: EfficientNetB0 · Explainability: Grad-CAM · Generated on ${new Date().toLocaleDateString()}
        </div>
      </body>
      </html>
    `
    win.document.write(content)
    win.document.close()
    win.focus()
    setTimeout(() => { win.print(); setPdfLoading(false) }, 600)
  }

  // Choose which image to show in main viewer
  const displayedImg = (activeTab === 'heatmap' && heatmapUrl && !heatmapError) ? heatmapUrl : imageUrl

  return (
    /* ── Overlay ─────────────────────────────────────────────── */
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Report details: ${report.disease}`}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Blurred dark backdrop */}
      <div className="absolute inset-0 bg-slate-950/85 backdrop-blur-md" onClick={onClose} />

      {/* Modal panel */}
      <div className="relative z-10 w-full max-w-4xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-700/60 rounded-3xl shadow-2xl overflow-hidden animate-scale-in">

        {/* ── Header ─────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-clinical-500/10 border border-clinical-500/20">
              <FileText className="w-4 h-4 text-clinical-400" />
            </div>
            <div>
              <h2 className="font-display font-bold text-white text-base leading-tight">
                Radiology Report #{report.id}
              </h2>
              <p className="text-xs text-slate-400">
                AI Diagnostic Summary & Explainable Attention
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Download PDF */}
            <button
              id={`btn-download-pdf-${report.id}`}
              onClick={handleDownloadPDF}
              disabled={pdfLoading}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 bg-slate-800 border border-slate-700 hover:border-clinical-500/50 hover:text-clinical-300 transition-all disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              {pdfLoading ? 'Preparing…' : 'Download PDF Report'}
            </button>

            {/* Close */}
            <button
              id={`btn-close-modal-${report.id}`}
              onClick={onClose}
              aria-label="Close report"
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-700 transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ── Scrollable body ─────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Top grid — image visualizer + summary */}
          <div className="grid md:grid-cols-12 gap-5 items-start">

            {/* Visualizer column (7 cols) */}
            <div className="md:col-span-7 space-y-2">
              
              {/* Tabs for switching between Grad-CAM & Original */}
              <div className="flex items-center justify-between bg-slate-950 p-1.5 rounded-xl border border-slate-800">
                <div className="flex gap-1">
                  {heatmapUrl && !heatmapError && (
                    <button
                      type="button"
                      onClick={() => setActiveTab('heatmap')}
                      className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                        activeTab === 'heatmap'
                          ? 'bg-gradient-to-r from-amber-500 to-red-500 text-white shadow-md'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Flame className="w-3 h-3" />
                      Grad-CAM
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => setActiveTab('original')}
                    className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      activeTab === 'original'
                        ? 'bg-clinical-600 text-white shadow-md'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Eye className="w-3 h-3" />
                    Original
                  </button>

                  {heatmapUrl && !heatmapError && (
                    <button
                      type="button"
                      onClick={() => setActiveTab('split')}
                      className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                        activeTab === 'split'
                          ? 'bg-indigo-600 text-white shadow-md'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <SplitSquareVertical className="w-3 h-3" />
                      Side-by-Side
                    </button>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => setZoomed(true)}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                  <span>Zoom</span>
                </button>
              </div>

              {/* Main image box */}
              <div className="relative group rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 min-h-[260px] max-h-[340px] flex items-center justify-center p-2">
                {!imgError ? (
                  activeTab === 'split' && heatmapUrl ? (
                    <div className="grid grid-cols-2 gap-2 w-full">
                      <div className="relative bg-black rounded-lg overflow-hidden flex flex-col items-center">
                        <img src={imageUrl} alt="Source" className="w-full h-52 object-contain" />
                        <span className="absolute top-1 left-1 px-1.5 py-0.5 bg-black/80 text-[9px] font-mono text-slate-300 rounded">ORIGINAL</span>
                      </div>
                      <div className="relative bg-black rounded-lg overflow-hidden flex flex-col items-center">
                        <img src={heatmapUrl} alt="Grad-CAM" className="w-full h-52 object-contain" />
                        <span className="absolute top-1 left-1 px-1.5 py-0.5 bg-red-600/90 text-[9px] font-mono text-white rounded">GRAD-CAM</span>
                      </div>
                    </div>
                  ) : (
                    <>
                      <img
                        src={displayedImg}
                        alt={`Chest X-ray — ${report.disease}`}
                        className="w-full h-full object-contain max-h-[320px]"
                        onError={() => {
                          if (activeTab === 'heatmap') {
                            setHeatmapError(true)
                            setActiveTab('original')
                          } else {
                            setImgError(true)
                          }
                        }}
                      />
                      <div className="absolute top-3 left-3 px-2 py-0.5 bg-black/70 backdrop-blur-md rounded text-[10px] font-mono text-white border border-white/10">
                        {activeTab === 'heatmap' ? 'GRAD-CAM ATTENTION' : 'SOURCE RADIOGRAPH'}
                      </div>
                    </>
                  )
                ) : (
                  <div className="text-slate-600 flex flex-col items-center gap-2 p-8">
                    <ImageOff className="w-10 h-10" />
                    <span className="text-sm">Image unavailable</span>
                  </div>
                )}
              </div>

              {/* Colormap scale note when heatmap is active */}
              {heatmapUrl && activeTab === 'heatmap' && (
                <div className="px-3 py-2 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                  <span className="flex items-center gap-1.5 text-amber-400 font-semibold">
                    <Sparkles className="w-3.5 h-3.5" />
                    Grad-CAM Focus:
                  </span>
                  <span>Red/Yellow indicates strongest feature saliency</span>
                </div>
              )}
            </div>

            {/* Summary column (5 cols) */}
            <div className="md:col-span-5 space-y-4 flex flex-col justify-center">

              {/* Disease badge */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-4 space-y-1.5">
                <p className="text-xs text-slate-500 uppercase tracking-widest font-medium">Diagnosis</p>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-base font-bold border ${diseaseBadgeClass(report.disease)}`}>
                    {report.disease.includes('No Finding')
                      ? <CheckCircle className="w-4 h-4" />
                      : <AlertTriangle className="w-4 h-4" />}
                    {report.disease}
                  </span>
                </div>
              </div>

              {/* Confidence */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-medium">
                    AI Confidence
                  </p>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${colors.bg} ${colors.text}`}>
                    {pct >= 90 ? 'HIGH' : pct >= 75 ? 'MODERATE' : 'LOW'}
                  </span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className={`font-display font-extrabold text-3xl ${colors.text}`}>{pct}%</span>
                  <span className="text-xs text-slate-500 font-mono">certainty</span>
                </div>
                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-gradient-to-r ${colors.bar} rounded-full transition-all duration-1000`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>

              {/* Date / time */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-4">
                <p className="text-xs text-slate-500 uppercase tracking-widest font-medium mb-1.5">Analysis Date</p>
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Calendar className="w-4 h-4 text-slate-500" />
                  <span>{dateStr}</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-slate-400">{timeStr}</span>
                </div>
              </div>

              {/* Mobile PDF button */}
              <button
                onClick={handleDownloadPDF}
                disabled={pdfLoading}
                className="sm:hidden flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-slate-300 hover:border-clinical-500/50 transition-all disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                {pdfLoading ? 'Preparing…' : 'Download PDF Report'}
              </button>
            </div>
          </div>

          {/* Divider */}
          <div className="h-px bg-slate-800" />

          {/* Full report text */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-clinical-400" />
              <p className="text-sm font-semibold text-slate-200">Radiology Findings & Impression</p>
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5">
              {report.report_text ? (
                <pre className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
                  {report.report_text}
                </pre>
              ) : (
                <p className="text-sm text-slate-500 italic">
                  Full report text is not available for this entry.
                </p>
              )}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex items-start gap-2.5 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-200/80 leading-relaxed">
              This report and Grad-CAM visualization are AI-generated assistive draft artifacts. Review and sign-off by a licensed radiologist or physician is required before clinical intervention.
            </p>
          </div>
        </div>
      </div>

      {/* ── Fullscreen zoom lightbox ─────────────────────────── */}
      {zoomed && (
        <div
          className="fixed inset-0 z-[60] bg-black/95 flex items-center justify-center p-4 cursor-zoom-out"
          onClick={() => setZoomed(false)}
        >
          <button
            onClick={() => setZoomed(false)}
            className="absolute top-4 right-4 p-2.5 rounded-xl bg-slate-800 text-slate-300 hover:text-white transition-colors z-10"
          >
            <X className="w-5 h-5" />
          </button>
          <img
            src={displayedImg}
            alt="X-ray full size view"
            className="max-w-full max-h-[90vh] object-contain rounded-xl"
            onError={() => { setImgError(true); setZoomed(false) }}
          />
        </div>
      )}
    </div>
  )
}

export default ReportModal
