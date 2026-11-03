import React, { useState, useCallback } from 'react'
import { Scan, Zap, ArrowRight, X } from 'lucide-react'
import Navbar       from '../components/Navbar'
import UploadSection from '../components/UploadSection'
import ResultCard   from '../components/ResultCard'
import Loader       from '../components/Loader'
import { predictDisease, API_BASE_URL, getFullImageUrl } from '../services/api'

/**
 * Home — main page that orchestrates the full X-ray diagnosis workflow.
 *
 * State machine:
 *   idle → loading → result
 *                 ↘ error
 */
function Home() {
  /* ── State ─────────────────────────────────────────────── */
  const [file,    setFile]    = useState(null)   // Selected File object
  const [preview, setPreview] = useState(null)   // Blob URL for preview

  const [status,  setStatus]  = useState('idle') // 'idle' | 'loading' | 'result' | 'error'
  const [result,  setResult]  = useState(null)   // API response object
  const [apiError, setApiError] = useState(null)  // Error message string

  /* ── Handlers ──────────────────────────────────────────── */
  const handleFileChange = useCallback((newFile, newPreview) => {
    // Revoke old preview URL to avoid memory leaks
    if (preview) URL.revokeObjectURL(preview)
    setFile(newFile)
    setPreview(newPreview)
    // Reset downstream state when a new file is chosen
    setResult(null)
    setApiError(null)
    setStatus('idle')
  }, [preview])

  const handleAnalyze = async () => {
    if (!file) return

    setStatus('loading')
    setApiError(null)
    setResult(null)

    try {
      const data = await predictDisease(file)
      setResult(data)
      setStatus('result')
    } catch (err) {
      console.error('Prediction API error:', err)

      // Determine a user-friendly message
      let message = 'Something went wrong. Please try again.'
      if (err.response) {
        message = err.response.data?.detail
          || `Server error ${err.response.status}. Please check the backend.`
      } else if (err.request) {
        message = `Cannot reach the server. Make sure the backend is reachable at ${API_BASE_URL}.`
      }

      setApiError(message)
      setStatus('error')
    }
  }

  const handleReset = useCallback(() => {
    if (preview) URL.revokeObjectURL(preview)
    setFile(null)
    setPreview(null)
    setResult(null)
    setApiError(null)
    setStatus('idle')
  }, [preview])

  /* ── Derived ───────────────────────────────────────────── */
  const isLoading  = status === 'loading'
  const hasResult  = status === 'result'
  const hasError   = status === 'error'
  const canAnalyze = !!file && !isLoading

  /* ── Render ────────────────────────────────────────────── */
  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      <Navbar />

      {/* ── Hero strip ──────────────────────────────────── */}
      <div className="bg-gradient-to-r from-navy-900 via-navy-800 to-clinical-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 md:py-14">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">

            {/* Left text */}
            <div className="space-y-3 max-w-xl">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 rounded-full text-xs font-medium text-clinical-200 border border-white/15">
                <Zap className="w-3.5 h-3.5" />
                Powered by Deep Learning
              </div>
              <h1 className="font-display font-extrabold text-3xl md:text-4xl leading-tight">
                AI X-ray Diagnosis
                <span className="block text-clinical-300">System</span>
              </h1>
              <p className="text-slate-300 text-sm leading-relaxed max-w-sm">
                Upload a chest X-ray image and receive an instant AI-powered analysis
                with disease prediction and a preliminary radiology report.
              </p>
            </div>

            {/* Right stats */}
            <div className="grid grid-cols-3 gap-3 md:gap-5 text-center">
              {[
                { label: 'Accuracy',  value: '94.2%' },
                { label: 'Diseases',  value: '14+'   },
                { label: 'Avg. Time', value: '< 3s'  },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="bg-white/10 backdrop-blur-sm rounded-2xl px-4 py-3 border border-white/10"
                >
                  <p className="font-display font-bold text-2xl text-white">{value}</p>
                  <p className="text-[11px] text-clinical-200 mt-0.5">{label}</p>
                </div>
              ))}
            </div>

          </div>
        </div>
      </div>

      {/* ── Main content ─────────────────────────────────── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-5 gap-6 items-start">

          {/* ═══ Left panel — Upload ═════════════════════ */}
          <div className="lg:col-span-2 space-y-5">

            {/* Card */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-card p-6 space-y-5">

              {/* Section header */}
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-clinical-50">
                  <Scan className="w-5 h-5 text-clinical-600" />
                </div>
                <div>
                  <h2 className="font-display font-bold text-navy-900 text-base">Upload X-ray</h2>
                  <p className="text-xs text-slate-400">Select or drag an image to begin</p>
                </div>
              </div>

              {/* Divider */}
              <div className="h-px bg-slate-100" />

              {/* Upload zone */}
              <UploadSection
                file={file}
                preview={preview}
                onFileChange={handleFileChange}
                error={hasError ? apiError : null}
              />

              {/* Analyze button */}
              <button
                onClick={handleAnalyze}
                disabled={!canAnalyze}
                className={[
                  'w-full flex items-center justify-center gap-3 py-3.5 rounded-2xl font-display font-semibold text-sm transition-all duration-300',
                  canAnalyze
                    ? 'bg-gradient-to-r from-clinical-600 to-navy-700 text-white shadow-lg hover:shadow-glow hover:scale-[1.01] active:scale-[0.99]'
                    : 'bg-slate-100 text-slate-300 cursor-not-allowed',
                ].join(' ')}
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Analyzing…
                  </>
                ) : (
                  <>
                    <Scan className="w-4 h-4" />
                    Analyze X-ray
                    {canAnalyze && <ArrowRight className="w-4 h-4 ml-auto" />}
                  </>
                )}
              </button>
            </div>

            {/* Info pills */}
            <div className="flex flex-wrap gap-2">
              {[
                'Chest Pathology',
                'Pneumonia',
                'Cardiomegaly',
                'Effusion',
                'Atelectasis',
                '+ 9 more',
              ].map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-500 font-medium shadow-sm"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          {/* ═══ Right panel — Results / Loader / Placeholder ═ */}
          <div className="lg:col-span-3">

            {/* Loading state */}
            {isLoading && (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-card p-8">
                <Loader message="Analyzing your X-ray image…" />
              </div>
            )}

            {/* Error state (non-file error — API errors) */}
            {hasError && !result && (
              <div className="bg-white rounded-3xl border border-red-200 shadow-card p-8 animate-slide-up">
                <div className="text-center space-y-4">
                  <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto">
                    <X className="w-7 h-7 text-red-500" />
                  </div>
                  <div>
                    <h3 className="font-display font-bold text-navy-900 text-lg mb-1">Analysis Failed</h3>
                    <p className="text-sm text-slate-500 max-w-sm mx-auto">{apiError}</p>
                  </div>
                  <button
                    onClick={handleAnalyze}
                    disabled={!file}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-clinical-600 text-white text-sm font-semibold hover:bg-clinical-700 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              </div>
            )}

            {/* Result card */}
            {hasResult && result && (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-card p-6">
                <div className="flex items-center gap-3 mb-5">
                  <div className="p-2.5 rounded-xl bg-clinical-50">
                    <Scan className="w-5 h-5 text-clinical-600" />
                  </div>
                  <div>
                    <h2 className="font-display font-bold text-navy-900 text-base">Analysis Complete</h2>
                    <p className="text-xs text-slate-400">AI-generated result — for review only</p>
                  </div>
                </div>
                <div className="h-px bg-slate-100 mb-5" />

                <ResultCard
                  disease={result.disease}
                  confidence={result.confidence}
                  report={result.report}
                  preview={preview}
                  heatmapUrl={result.heatmap_url ? getFullImageUrl(result.heatmap_url) : (result.heatmap_path ? getFullImageUrl(result.heatmap_path) : '')}
                  file={file}
                  onReset={handleReset}
                />
              </div>
            )}

            {/* Idle placeholder */}
            {status === 'idle' && (
              <div className="bg-white rounded-3xl border border-dashed border-slate-200 p-12 flex flex-col items-center justify-center text-center gap-5 min-h-80 animate-fade-in">
                <div className="w-20 h-20 rounded-3xl bg-clinical-50 flex items-center justify-center">
                  <Scan className="w-10 h-10 text-clinical-200" />
                </div>
                <div>
                  <h3 className="font-display font-bold text-navy-900 text-lg mb-1">
                    Results will appear here
                  </h3>
                  <p className="text-sm text-slate-400 max-w-xs">
                    Upload a chest X-ray image and click{' '}
                    <span className="font-semibold text-clinical-600">Analyze X-ray</span>{' '}
                    to get an AI-powered diagnosis.
                  </p>
                </div>

                {/* Step indicators */}
                <div className="flex items-center gap-2 mt-2">
                  {['Upload', 'Analyze', 'Review'].map((step, i) => (
                    <React.Fragment key={step}>
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-7 h-7 rounded-full bg-slate-100 border-2 border-slate-200 flex items-center justify-center text-xs font-bold text-slate-400">
                          {i + 1}
                        </div>
                        <span className="text-[10px] text-slate-400 font-medium">{step}</span>
                      </div>
                      {i < 2 && (
                        <div className="w-8 h-px bg-slate-200 mb-4" />
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>
      </main>

      {/* ── Footer ───────────────────────────────────────── */}
      <footer className="border-t border-slate-200 bg-white mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-slate-400">
            © 2024 AI X-ray Diagnosis System · For research and educational use only
          </p>
          <div className="flex gap-4 text-xs text-slate-400">
            <a href="#" className="hover:text-clinical-600 transition-colors">Privacy</a>
            <a href="#" className="hover:text-clinical-600 transition-colors">Terms</a>
            <a href="#" className="hover:text-clinical-600 transition-colors">Docs</a>
          </div>
        </div>
      </footer>
    
    </div>
  )
}

export default Home
