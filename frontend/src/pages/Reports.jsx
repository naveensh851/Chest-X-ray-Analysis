import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ClipboardList, Calendar, Activity, TrendingUp,
  AlertCircle, ImageOff, ArrowLeft, RefreshCw, Scan, Eye,
} from 'lucide-react'
import Navbar      from '../components/Navbar'
import ReportModal from '../components/ReportModal'
import { getReports, API_BASE_URL } from '../services/api'

/** Badge colour based on disease name */
function diseaseBadgeClass(disease) {
  const d = (disease || '').toLowerCase()
  if (d.includes('pneumonia'))   return 'bg-red-500/10 text-red-400 border-red-500/20'
  if (d.includes('cardio'))      return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
  if (d.includes('effusion'))    return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
  if (d.includes('atelectasis')) return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  if (d.includes('no finding'))  return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  return 'bg-clinical-500/10 text-clinical-400 border-clinical-500/20'
}

/** Confidence percentage badge */
function ConfidencePill({ confidence }) {
  const pct   = Math.round(confidence * 100)
  const color = pct >= 90 ? 'text-emerald-400' : pct >= 75 ? 'text-yellow-400' : 'text-red-400'
  return <span className={`font-bold font-display ${color}`}>{pct}%</span>
}

/**
 * ReportCard — single clickable card in the list.
 *
 * Props:
 *   report   — report object from /reports API
 *   index    — list index (used for staggered animation delay)
 *   onSelect — called with report when card or button is clicked
 */
function ReportCard({ report, index, onSelect }) {
  const [imgError, setImgError] = useState(false)
  const date    = new Date(report.created_at)
  const dateStr = date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  const timeStr = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

  // image_url is now provided directly by the backend
  const imageUrl = report.image_url || `${API_BASE_URL}${report.image_path}`

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`View report: ${report.disease}`}
      onClick={() => onSelect(report)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(report)}
      className="group bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden
                 hover:border-clinical-500/50 hover:bg-slate-800/80 hover:shadow-lg hover:shadow-clinical-900/20
                 transition-all duration-300 animate-slide-up cursor-pointer outline-none
                 focus-visible:ring-2 focus-visible:ring-clinical-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="flex gap-0">

        {/* ── Thumbnail ───────────────────────────────────── */}
        <div className="w-24 sm:w-32 flex-shrink-0 bg-slate-900/60 flex items-center justify-center overflow-hidden relative">
          {!imgError ? (
            <>
              <img
                src={imageUrl}
                alt={`X-ray — ${report.disease}`}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                onError={() => setImgError(true)}
              />
              {/* Hover zoom hint */}
              <div className="absolute inset-0 bg-clinical-900/0 group-hover:bg-clinical-900/30 flex items-center justify-center transition-all duration-300 opacity-0 group-hover:opacity-100">
                <Eye className="w-5 h-5 text-white drop-shadow" />
              </div>
            </>
          ) : (
            <div className="p-4 text-slate-600 flex flex-col items-center gap-1">
              <ImageOff className="w-6 h-6" />
              <span className="text-[9px] text-center">No preview</span>
            </div>
          )}
        </div>

        {/* ── Content ─────────────────────────────────────── */}
        <div className="flex-1 p-4 sm:p-5 flex flex-col justify-between gap-2.5">

          {/* Top row: disease badge + date */}
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${diseaseBadgeClass(report.disease)}`}>
              {report.disease}
            </span>
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <Calendar className="w-3.5 h-3.5" />
              <span>{dateStr}</span>
              <span className="opacity-50">·</span>
              <span>{timeStr}</span>
            </div>
          </div>

          {/* Confidence row */}
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <TrendingUp className="w-4 h-4 text-slate-500" />
            Confidence: <ConfidencePill confidence={report.confidence} />
            <span className="ml-auto text-xs text-slate-600 font-mono">#{report.id}</span>
          </div>

          {/* Mini confidence bar */}
          <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-clinical-500 to-navy-500 rounded-full transition-all duration-700"
              style={{ width: `${Math.round(report.confidence * 100)}%` }}
            />
          </div>

          {/* View Report CTA */}
          <div className="flex items-center justify-between pt-0.5">
            {report.report_text ? (
              <span className="text-[10px] text-slate-600 italic">Report text available</span>
            ) : (
              <span className="text-[10px] text-slate-700 italic">No report text</span>
            )}
            <button
              id={`btn-view-report-${report.id}`}
              onClick={(e) => { e.stopPropagation(); onSelect(report) }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-clinical-600/10 border border-clinical-500/20
                         text-clinical-400 text-xs font-semibold hover:bg-clinical-600/20 hover:border-clinical-500/40
                         group-hover:bg-clinical-600/20 transition-all duration-200"
            >
              <Eye className="w-3.5 h-3.5" />
              View Report
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Reports — main page listing all saved X-ray reports for the user.
 * Clicking any card (or the "View Report" button) opens a full-detail modal.
 */
function Reports() {
  const navigate = useNavigate()

  const [reports,        setReports]        = useState([])
  const [loading,        setLoading]        = useState(true)
  const [error,          setError]          = useState(null)
  const [selectedReport, setSelectedReport] = useState(null)  // modal state

  const fetchReports = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getReports()
      setReports(data)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        (err.request ? 'Cannot reach server.' : 'Failed to load reports.')
      setError(typeof msg === 'string' ? msg : 'Failed to load reports.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchReports() }, [])

  /* ── Stats ─────────────────────────────────────────────────── */
  const totalReports  = reports.length
  const diseases      = [...new Set(reports.map(r => r.disease))]
  const avgConfidence = reports.length
    ? Math.round((reports.reduce((s, r) => s + r.confidence, 0) / reports.length) * 100)
    : 0

  return (
    <div className="flex flex-col min-h-screen bg-slate-900 text-slate-100">
      <Navbar />

      {/* ── Header ──────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-navy-900 via-slate-900 to-clinical-900/40 border-b border-slate-800">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-10">
          <div className="flex flex-col md:flex-row md:items-center gap-6 justify-between">

            <div className="space-y-2">
              <button
                id="btn-back-home"
                onClick={() => navigate('/')}
                className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-clinical-400 transition-colors mb-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Diagnosis
              </button>
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-clinical-500/10 border border-clinical-500/20">
                  <ClipboardList className="w-5 h-5 text-clinical-400" />
                </div>
                <div>
                  <h1 className="font-display font-bold text-white text-2xl">My Reports</h1>
                  <p className="text-slate-400 text-sm">
                    All your saved X-ray analyses · click any card to view full details
                  </p>
                </div>
              </div>
            </div>

            {/* Stats strip */}
            {!loading && !error && (
              <div className="grid grid-cols-3 gap-3 text-center">
                {[
                  { label: 'Total Scans',     value: totalReports,        icon: Scan       },
                  { label: 'Unique Diseases', value: diseases.length,     icon: Activity   },
                  { label: 'Avg. Confidence', value: `${avgConfidence}%`, icon: TrendingUp },
                ].map(({ label, value, icon: Icon }) => (
                  <div key={label} className="bg-slate-800/60 border border-slate-700/50 rounded-2xl px-4 py-3">
                    <Icon className="w-4 h-4 text-clinical-400 mx-auto mb-1" />
                    <p className="font-display font-bold text-white text-xl">{value}</p>
                    <p className="text-[10px] text-slate-400">{label}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Main content ────────────────────────────────────── */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-10 h-10 rounded-full border-2 border-slate-700 border-t-clinical-500 animate-spin" />
            <p className="text-slate-400 text-sm">Loading your reports…</p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="flex flex-col items-center gap-5 py-20">
            <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
              <AlertCircle className="w-7 h-7 text-red-400" />
            </div>
            <div className="text-center">
              <h3 className="font-display font-bold text-white text-lg mb-1">Failed to load reports</h3>
              <p className="text-slate-400 text-sm max-w-sm">{error}</p>
            </div>
            <button
              id="btn-retry-reports"
              onClick={fetchReports}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-clinical-600 text-white text-sm font-semibold hover:bg-clinical-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" /> Try Again
            </button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && reports.length === 0 && (
          <div className="flex flex-col items-center gap-5 py-20 text-center">
            <div className="w-20 h-20 rounded-3xl bg-slate-800 border border-slate-700 flex items-center justify-center">
              <ClipboardList className="w-10 h-10 text-slate-600" />
            </div>
            <div>
              <h3 className="font-display font-bold text-white text-xl mb-2">No reports yet</h3>
              <p className="text-slate-400 text-sm max-w-xs">
                You haven't analysed any X-rays yet. Head back to the home page to get started.
              </p>
            </div>
            <button
              id="btn-go-analyse"
              onClick={() => navigate('/')}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-clinical-600 to-navy-700 text-white text-sm font-semibold shadow-lg hover:shadow-glow transition-all"
            >
              <Scan className="w-4 h-4" /> Analyse an X-ray
            </button>
          </div>
        )}

        {/* Report list */}
        {!loading && !error && reports.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">
                {totalReports} {totalReports === 1 ? 'report' : 'reports'} found
                <span className="ml-2 text-slate-600 text-xs">· click any card to view full details</span>
              </p>
              <button
                id="btn-refresh-reports"
                onClick={fetchReports}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-clinical-400 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
            </div>

            {reports.map((report, i) => (
              <ReportCard
                key={report.id}
                report={report}
                index={i}
                onSelect={setSelectedReport}
              />
            ))}
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 mt-8 py-5 text-center text-xs text-slate-600">
        © 2024 AI X-ray Diagnosis System · For research and educational use only
      </footer>

      {/* ── Report Detail Modal ──────────────────────────────── */}
      {selectedReport && (
        <ReportModal
          report={selectedReport}
          onClose={() => setSelectedReport(null)}
        />
      )}
    </div>
  )
}

export default Reports
