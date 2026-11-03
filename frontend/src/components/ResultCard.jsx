import React, { useState, useEffect } from 'react'
import {
  ShieldAlert, ShieldCheck, ActivitySquare,
  FileText, Percent, ChevronDown, ChevronUp,
  Download, RotateCcw, Info, Flame, Eye,
  SplitSquareVertical, ZoomIn, X, Sliders, Sparkles
} from 'lucide-react'

/**
 * Severity thresholds for confidence score styling.
 */
const getSeverity = (disease, confidence) => {
  const lowRisk = ['Normal', 'Healthy', 'No Finding']
  const isNormal = lowRisk.some(k => (disease || '').toLowerCase().includes(k.toLowerCase()))

  if (isNormal)             return { label: 'Normal',   color: 'emerald', ring: 'emerald' }
  if (confidence >= 0.85)   return { label: 'High',     color: 'red',     ring: 'red'     }
  if (confidence >= 0.65)   return { label: 'Moderate', color: 'amber',   ring: 'amber'   }
  return                           { label: 'Low',      color: 'yellow',  ring: 'yellow'  }
}

/**
 * Animated confidence bar that counts up on mount.
 */
function ConfidenceBar({ value }) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => setWidth(value * 100), 300)
    return () => clearTimeout(timer)
  }, [value])

  const pct = Math.round(value * 100)
  const color =
    pct >= 85 ? 'from-red-400 to-red-600'     :
    pct >= 65 ? 'from-amber-400 to-amber-600' :
               'from-emerald-400 to-emerald-600'

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Confidence Score</span>
        <span className="font-display font-bold text-navy-800 text-lg">{pct}%</span>
      </div>
      <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden shadow-inner-lg">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${color} transition-all duration-1000 ease-out`}
          style={{ width: `${width}%` }}
        />
      </div>
      <p className="text-[11px] text-slate-400">
        Model certainty for the predicted diagnosis
      </p>
    </div>
  )
}

/**
 * ResultCard — displays the prediction results and explainable Grad-CAM heatmap.
 *
 * @param {string} disease      - Predicted disease label
 * @param {number} confidence   - Confidence score 0–1
 * @param {string} report       - Generated textual report
 * @param {string} preview      - Object URL of the uploaded raw X-ray
 * @param {string} heatmapUrl   - Full URL to the generated Grad-CAM heatmap
 * @param {File}   file         - Original file for download actions
 * @param {Function} onReset    - Callback to reset and start over
 */
function ResultCard({ disease, confidence, report, preview, heatmapUrl, file, onReset }) {
  const [reportExpanded, setReportExpanded] = useState(false)
  const [viewMode, setViewMode] = useState(heatmapUrl ? 'heatmap' : 'original') // 'heatmap' | 'original' | 'split'
  const [opacity, setOpacity] = useState(100) // 0-100 opacity for overlay slider
  const [zoomImg, setZoomImg] = useState(null) // lightbox URL

  useEffect(() => {
    if (heatmapUrl) {
      setViewMode('heatmap')
    } else {
      setViewMode('original')
    }
  }, [heatmapUrl])

  const severity = getSeverity(disease, confidence)
  const isNormal = severity.label === 'Normal'

  // Color maps per severity
  const colorMap = {
    emerald: {
      bg:     'bg-emerald-50',
      border: 'border-emerald-200',
      badge:  'bg-emerald-100 text-emerald-700 border-emerald-200',
      icon:   'text-emerald-600',
      ring:   'ring-emerald-200',
    },
    red: {
      bg:     'bg-red-50',
      border: 'border-red-200',
      badge:  'bg-red-100 text-red-700 border-red-200',
      icon:   'text-red-600',
      ring:   'ring-red-200',
    },
    amber: {
      bg:     'bg-amber-50',
      border: 'border-amber-200',
      badge:  'bg-amber-100 text-amber-700 border-amber-200',
      icon:   'text-amber-600',
      ring:   'ring-amber-200',
    },
    yellow: {
      bg:     'bg-yellow-50',
      border: 'border-yellow-200',
      badge:  'bg-yellow-100 text-yellow-800 border-yellow-200',
      icon:   'text-yellow-600',
      ring:   'ring-yellow-200',
    },
  }

  const c = colorMap[severity.color]

  return (
    <div className="animate-slide-up space-y-5">

      {/* ── Header banner ─────────────────────────────── */}
      <div className={`rounded-2xl border ${c.bg} ${c.border} px-5 py-4 flex items-center gap-4`}>
        <div className={`p-2.5 rounded-xl ${c.bg} ring-2 ${c.ring}`}>
          {isNormal
            ? <ShieldCheck className={`w-6 h-6 ${c.icon}`} />
            : <ShieldAlert className={`w-6 h-6 ${c.icon}`} />
          }
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-0.5">
            Diagnosis Result
          </p>
          <h2 className="font-display font-bold text-navy-900 text-xl leading-tight truncate">
            {disease}
          </h2>
        </div>
        <span className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-bold border ${c.badge}`}>
          {severity.label} Risk
        </span>
      </div>

      {/* ── Main grid ─────────────────────────────────── */}
      <div className="grid lg:grid-cols-12 gap-5 items-start">

        {/* ── Image & Grad-CAM Visualizer (7 cols) ─────── */}
        <div className="lg:col-span-7 space-y-3">
          
          {/* Visualizer card */}
          <div className="rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 shadow-xl flex flex-col">
            
            {/* View Mode Toolbar */}
            <div className="px-3 py-2.5 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 p-1 bg-slate-950/80 rounded-xl border border-slate-800">
                {heatmapUrl && (
                  <button
                    type="button"
                    onClick={() => setViewMode('heatmap')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      viewMode === 'heatmap'
                        ? 'bg-gradient-to-r from-amber-500 to-red-500 text-white shadow-md shadow-red-950/50'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <Flame className="w-3.5 h-3.5" />
                    Grad-CAM
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => setViewMode('original')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    viewMode === 'original'
                      ? 'bg-clinical-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  Original
                </button>

                {heatmapUrl && (
                  <button
                    type="button"
                    onClick={() => setViewMode('split')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      viewMode === 'split'
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <SplitSquareVertical className="w-3.5 h-3.5" />
                    Side-by-Side
                  </button>
                )}
              </div>

              {/* Lightbox zoom action */}
              <button
                type="button"
                onClick={() => setZoomImg(viewMode === 'original' ? preview : (heatmapUrl || preview))}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs text-slate-400 hover:text-white hover:bg-slate-800/80 border border-slate-800 transition-colors"
                title="Zoom view"
              >
                <ZoomIn className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Zoom</span>
              </button>
            </div>

            {/* Image display canvas */}
            <div className="relative min-h-[280px] sm:min-h-[320px] bg-slate-950 flex items-center justify-center p-3 select-none">
              
              {/* Single / Heatmap view */}
              {viewMode !== 'split' && (
                <div className="relative w-full max-h-[360px] flex items-center justify-center overflow-hidden rounded-xl">
                  {/* Base Original Image */}
                  <img
                    src={preview}
                    alt="Source Chest X-ray"
                    className="w-full h-full object-contain max-h-[360px]"
                  />

                  {/* Overlaid Grad-CAM Heatmap with interactive opacity */}
                  {heatmapUrl && viewMode === 'heatmap' && (
                    <img
                      src={heatmapUrl}
                      alt="Grad-CAM Activation Heatmap"
                      style={{ opacity: opacity / 100 }}
                      className="absolute inset-0 w-full h-full object-contain max-h-[360px] transition-opacity duration-150 pointer-events-none"
                    />
                  )}

                  {/* Corner tags */}
                  <div className="absolute top-2 left-2 px-2.5 py-1 bg-black/70 backdrop-blur-md rounded-lg text-[10px] font-mono text-white/90 border border-white/10">
                    {viewMode === 'heatmap' ? 'GRAD-CAM OVERLAY' : 'SOURCE RADIOGRAPH'}
                  </div>

                  {heatmapUrl && viewMode === 'heatmap' && (
                    <div className="absolute top-2 right-2 px-2.5 py-1 bg-red-500/80 backdrop-blur-md rounded-lg text-[10px] font-semibold text-white border border-red-400/30 flex items-center gap-1 shadow-lg">
                      <Sparkles className="w-3 h-3" />
                      XAI ACTIVE ({opacity}%)
                    </div>
                  )}
                </div>
              )}

              {/* Side-by-Side split view */}
              {viewMode === 'split' && heatmapUrl && (
                <div className="grid grid-cols-2 gap-3 w-full">
                  <div className="relative rounded-xl overflow-hidden bg-black border border-slate-800 flex flex-col items-center">
                    <img
                      src={preview}
                      alt="Original"
                      className="w-full h-48 sm:h-64 object-contain"
                    />
                    <div className="absolute top-2 left-2 px-2 py-0.5 bg-black/80 rounded text-[9px] font-mono text-slate-300">
                      ORIGINAL
                    </div>
                  </div>

                  <div className="relative rounded-xl overflow-hidden bg-black border border-slate-800 flex flex-col items-center">
                    <img
                      src={heatmapUrl}
                      alt="Grad-CAM"
                      className="w-full h-48 sm:h-64 object-contain"
                    />
                    <div className="absolute top-2 left-2 px-2 py-0.5 bg-red-600/80 rounded text-[9px] font-mono text-white">
                      GRAD-CAM
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Slider & Legend for Grad-CAM */}
            {heatmapUrl && viewMode === 'heatmap' && (
              <div className="px-4 py-3 bg-slate-900/80 border-t border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5 font-medium text-slate-300">
                    <Sliders className="w-3.5 h-3.5 text-amber-400" />
                    Heatmap Blend Opacity
                  </span>
                  <span className="font-mono text-slate-300 font-bold">{opacity}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={opacity}
                  onChange={(e) => setOpacity(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
                />
              </div>
            )}
          </div>

          {/* Grad-CAM Explanation and Color Scale Card */}
          {heatmapUrl ? (
            <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-slate-300 space-y-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <Flame className="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    Grad-CAM Interpretability
                  </h4>
                  <p className="text-[11px] text-slate-400">
                    EfficientNetB0 final convolutional activation (<code className="text-amber-400 font-mono">top_conv</code>)
                  </p>
                </div>
              </div>

              {/* Thermal colormap gradient bar */}
              <div className="space-y-1">
                <div className="h-2 rounded-full w-full bg-gradient-to-r from-blue-600 via-cyan-400 via-emerald-400 via-yellow-400 to-red-600 shadow-inner" />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>Low Attention (0.0)</span>
                  <span>Moderate Focus (0.5)</span>
                  <span className="text-red-400 font-semibold">Peak Pathology Activation (1.0)</span>
                </div>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                Warm red/yellow highlights identify class-discriminative regions that most heavily influenced the AI’s prediction of <strong className="text-slate-200">{disease}</strong>.
              </p>
            </div>
          ) : (
            <div className="p-3 rounded-xl bg-slate-100 border border-slate-200 text-slate-500 text-xs">
              Grad-CAM visualization was not generated for this image.
            </div>
          )}

        </div>

        {/* ── Metrics & Technical Card (5 cols) ───────── */}
        <div className="lg:col-span-5 rounded-2xl bg-white border border-slate-200 shadow-card p-5 space-y-5">
          
          {/* Confidence bar */}
          <ConfidenceBar value={confidence} />

          {/* Stats row with authentic EfficientNet + Grad-CAM details */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Model Architecture</p>
              <p className="text-xs font-mono font-semibold text-navy-800">EfficientNetB0</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Explainability</p>
              <p className="text-xs font-mono font-semibold text-clinical-600">Grad-CAM (top_conv)</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Input Resolution</p>
              <p className="text-xs font-mono font-semibold text-navy-800">224 × 224 × 3</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Target Classes</p>
              <p className="text-xs font-mono font-semibold text-navy-800">5 Pulmonary</p>
            </div>
          </div>

          {/* Target classes list pill */}
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100 space-y-1.5">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">Monitored Pathologies</p>
            <div className="flex flex-wrap gap-1">
              {['Infiltration', 'Effusion', 'Atelectasis', 'Nodule', 'Mass'].map(cls => (
                <span
                  key={cls}
                  className={`text-[10px] px-2 py-0.5 rounded-md font-medium ${
                    cls.toLowerCase() === disease.toLowerCase()
                      ? 'bg-clinical-600 text-white font-bold'
                      : 'bg-white border border-slate-200 text-slate-600'
                  }`}
                >
                  {cls}
                </span>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex gap-2 text-[11px] text-slate-500 bg-amber-50 border border-amber-200/80 rounded-xl px-3 py-2.5 leading-relaxed">
            <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <span>AI diagnostic assistance for research and triage support. Clinical correlation and licensed radiologist review required.</span>
          </div>
        </div>

      </div>

      {/* ── Report section ────────────────────────────── */}
      <div className="rounded-2xl bg-white border border-slate-200 shadow-card overflow-hidden">
        {/* Collapsible header */}
        <button
          type="button"
          onClick={() => setReportExpanded(v => !v)}
          className="w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50 transition-colors text-left"
          aria-expanded={reportExpanded}
        >
          <div className="p-2 rounded-lg bg-clinical-50">
            <FileText className="w-4 h-4 text-clinical-600" />
          </div>
          <div className="flex-1">
            <p className="font-display font-semibold text-navy-900 text-sm">Radiology Report</p>
            <p className="text-xs text-slate-400">AI-generated preliminary findings & impressions</p>
          </div>
          {reportExpanded
            ? <ChevronUp className="w-4 h-4 text-slate-400" />
            : <ChevronDown className="w-4 h-4 text-slate-400" />
          }
        </button>

        {/* Report body */}
        {reportExpanded && (
          <div className="px-5 pb-5 animate-fade-in">
            <div className="h-px bg-slate-100 mb-4" />
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
              <p className="text-sm text-slate-700 leading-relaxed font-mono whitespace-pre-wrap">
                {report}
              </p>
            </div>
            {/* Report metadata */}
            <div className="mt-3 flex gap-4 text-[11px] text-slate-400">
              <span>Generated: {new Date().toLocaleString()}</span>
              <span>·</span>
              <span>AI Draft — Pending Radiologist Review</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Actions row ───────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={onReset}
          className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 hover:border-slate-300 transition-all duration-200"
        >
          <RotateCcw className="w-4 h-4" />
          Analyze New Image
        </button>

        <button
          type="button"
          onClick={() => window.print()}
          className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-clinical-600 to-navy-700 text-white text-sm font-medium hover:from-clinical-700 hover:to-navy-800 transition-all duration-200 shadow-md hover:shadow-lg"
        >
          <Download className="w-4 h-4" />
          Export Clinical Report
        </button>
      </div>

      {/* ── Lightbox Zoom Modal ───────────────────────── */}
      {zoomImg && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-[70] bg-black/95 flex items-center justify-center p-4 cursor-zoom-out"
          onClick={() => setZoomImg(null)}
        >
          <button
            type="button"
            onClick={() => setZoomImg(null)}
            className="absolute top-4 right-4 p-2.5 rounded-xl bg-slate-800 text-slate-200 hover:text-white transition-colors z-10"
          >
            <X className="w-5 h-5" />
          </button>
          <img
            src={zoomImg}
            alt="Full size radiographic visualization"
            className="max-w-full max-h-[90vh] object-contain rounded-xl shadow-2xl"
          />
        </div>
      )}

    </div>
  )
}

export default ResultCard
