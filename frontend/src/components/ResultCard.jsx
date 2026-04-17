import React, { useState, useEffect } from 'react'
import {
  ShieldAlert, ShieldCheck, ActivitySquare,
  FileText, Percent, ChevronDown, ChevronUp,
  Download, RotateCcw, Info
} from 'lucide-react'

/**
 * Severity thresholds for confidence score styling.
 */
const getSeverity = (disease, confidence) => {
  const lowRisk = ['Normal', 'Healthy', 'No Finding']
  const isNormal = lowRisk.some(k => disease.toLowerCase().includes(k.toLowerCase()))

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
 * ResultCard — displays the prediction results after API response.
 *
 * @param {string} disease     - Predicted disease label
 * @param {number} confidence  - Confidence score 0–1
 * @param {string} report      - Generated textual report
 * @param {string} preview     - Object URL of the uploaded X-ray
 * @param {File}   file        - Original file for download actions
 * @param {Function} onReset   - Callback to reset and start over
 */
function ResultCard({ disease, confidence, report, preview, file, onReset }) {
  const [reportExpanded, setReportExpanded] = useState(false)
  const severity                            = getSeverity(disease, confidence)

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
            ? <ShieldCheck   className={`w-6 h-6 ${c.icon}`} />
            : <ShieldAlert   className={`w-6 h-6 ${c.icon}`} />
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
      <div className="grid md:grid-cols-2 gap-4">

        {/* X-ray image */}
        <div className="rounded-2xl overflow-hidden bg-slate-900 shadow-card relative group">
          <img
            src={preview}
            alt="Analyzed X-ray"
            className="w-full object-contain max-h-64"
          />
          {/* Scan line animation */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-40">
            <div
              className="scan-line absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-clinical-400 to-transparent"
              style={{ top: '50%' }}
            />
          </div>
          {/* Corner tags */}
          <div className="absolute top-2 left-2 px-2 py-1 bg-black/50 backdrop-blur-sm rounded-lg text-[10px] font-mono text-white/80">
            {file?.name?.slice(0, 24)}
          </div>
          <div className="absolute top-2 right-2 px-2 py-1 bg-clinical-500/80 backdrop-blur-sm rounded-lg text-[10px] font-mono text-white">
            ANALYZED
          </div>
        </div>

        {/* Metrics card */}
        <div className="rounded-2xl bg-white border border-slate-200 shadow-card p-5 space-y-5 flex flex-col justify-between">

          {/* Confidence bar */}
          <ConfidenceBar value={confidence} />

          {/* Stats row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Model</p>
              <p className="text-xs font-mono font-semibold text-navy-800">ResNet-50</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Version</p>
              <p className="text-xs font-mono font-semibold text-navy-800">v2.4.1</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Dataset</p>
              <p className="text-xs font-mono font-semibold text-navy-800">ChestX-ray14</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1 font-medium">Classes</p>
              <p className="text-xs font-mono font-semibold text-navy-800">14 diseases</p>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex gap-2 text-[11px] text-slate-400 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2.5">
            <Info className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
            <span>AI-assisted only. Consult a licensed physician for clinical decisions.</span>
          </div>
        </div>
      </div>

      {/* ── Report section ────────────────────────────── */}
      <div className="rounded-2xl bg-white border border-slate-200 shadow-card overflow-hidden">
        {/* Collapsible header */}
        <button
          onClick={() => setReportExpanded(v => !v)}
          className="w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50 transition-colors text-left"
          aria-expanded={reportExpanded}
        >
          <div className="p-2 rounded-lg bg-clinical-50">
            <FileText className="w-4 h-4 text-clinical-600" />
          </div>
          <div className="flex-1">
            <p className="font-display font-semibold text-navy-900 text-sm">Radiology Report</p>
            <p className="text-xs text-slate-400">AI-generated preliminary findings</p>
          </div>
          {reportExpanded
            ? <ChevronUp   className="w-4 h-4 text-slate-400" />
            : <ChevronDown className="w-4 h-4 text-slate-400" />
          }
        </button>

        {/* Report body */}
        {reportExpanded && (
          <div className="px-5 pb-5 animate-fade-in">
            <div className="h-px bg-slate-100 mb-4" />
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-sm text-slate-700 leading-relaxed font-mono whitespace-pre-wrap">
                {report}
              </p>
            </div>
            {/* Report metadata */}
            <div className="mt-3 flex gap-4 text-[11px] text-slate-400">
              <span>Generated: {new Date().toLocaleString()}</span>
              <span>·</span>
              <span>AI Draft — Pending Review</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Actions row ───────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={onReset}
          className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 hover:border-slate-300 transition-all duration-200"
        >
          <RotateCcw className="w-4 h-4" />
          Analyze New Image
        </button>

        <button
          onClick={() => window.print()}
          className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-clinical-600 to-navy-700 text-white text-sm font-medium hover:from-clinical-700 hover:to-navy-800 transition-all duration-200 shadow-md hover:shadow-lg"
        >
          <Download className="w-4 h-4" />
          Export Report
        </button>
      </div>

    </div>
  )
}

export default ResultCard
