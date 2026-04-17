import React, { useState, useRef, useCallback } from 'react'
import { UploadCloud, ImagePlus, X, CheckCircle2, AlertTriangle } from 'lucide-react'

// Accepted image MIME types
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp']
const MAX_SIZE_MB = 10

/**
 * UploadSection — drag-and-drop or click-to-browse image uploader.
 *
 * @param {File|null}   file        - Currently selected file (controlled)
 * @param {string|null} preview     - Object URL of the selected image
 * @param {Function}    onFileChange - Called with (file, previewUrl) or (null, null) on clear
 * @param {string|null} error       - External validation error message
 */
function UploadSection({ file, preview, onFileChange, error }) {
  const [isDragging, setIsDragging]   = useState(false)
  const [localError, setLocalError]   = useState(null)
  const inputRef                      = useRef(null)

  // ── Validation ──────────────────────────────────────────
  const validateFile = (f) => {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      return 'Unsupported file type. Please upload a JPEG, PNG, WebP, or BMP image.'
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File size exceeds ${MAX_SIZE_MB} MB limit.`
    }
    return null
  }

  const processFile = useCallback((f) => {
    const err = validateFile(f)
    if (err) {
      setLocalError(err)
      onFileChange(null, null)
      return
    }
    setLocalError(null)
    const url = URL.createObjectURL(f)
    onFileChange(f, url)
  }, [onFileChange])

  // ── Drag handlers ────────────────────────────────────────
  const handleDragOver  = (e) => { e.preventDefault(); setIsDragging(true)  }
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false) }
  const handleDrop      = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) processFile(droppedFile)
  }

  // ── Input change ─────────────────────────────────────────
  const handleInputChange = (e) => {
    const selected = e.target.files?.[0]
    if (selected) processFile(selected)
    // Reset input so the same file can be re-selected after clearing
    e.target.value = ''
  }

  // ── Clear selection ──────────────────────────────────────
  const handleClear = () => {
    setLocalError(null)
    onFileChange(null, null)
  }

  const displayError = localError || error

  return (
    <div className="space-y-4">

      {/* ── Drop zone ──────────────────────────────────── */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload X-ray image"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !preview && inputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && !preview && inputRef.current?.click()}
        className={[
          'relative rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer select-none overflow-hidden',
          isDragging
            ? 'border-clinical-500 bg-clinical-50 scale-[1.01] shadow-glow'
            : preview
            ? 'border-clinical-300 bg-white cursor-default'
            : 'border-slate-300 bg-white hover:border-clinical-400 hover:bg-clinical-50/50',
        ].join(' ')}
        style={{ minHeight: preview ? 'auto' : '220px' }}
      >

        {preview ? (
          /* ── Image preview ─────────────────────────── */
          <div className="relative group animate-scale-in">
            <img
              src={preview}
              alt="X-ray preview"
              className="w-full max-h-80 object-contain rounded-2xl bg-slate-900"
            />

            {/* Overlay on hover */}
            <div className="absolute inset-0 bg-navy-900/0 group-hover:bg-navy-900/30 rounded-2xl transition-colors duration-200 flex items-center justify-center">
              <button
                onClick={(e) => { e.stopPropagation(); handleClear() }}
                className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white/90 hover:bg-white rounded-full p-2 shadow-lg"
                aria-label="Remove image"
              >
                <X className="w-5 h-5 text-slate-700" />
              </button>
            </div>

            {/* File name badge */}
            <div className="absolute bottom-3 left-3 right-3 flex items-center gap-2 bg-navy-900/75 backdrop-blur-sm rounded-xl px-3 py-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span className="text-xs text-white font-medium truncate">{file?.name}</span>
              <span className="ml-auto text-xs text-slate-300 flex-shrink-0">
                {(file?.size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
          </div>

        ) : (
          /* ── Empty state ───────────────────────────── */
          <div className="flex flex-col items-center justify-center gap-4 py-14 px-6 text-center">
            <div className={[
              'w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300',
              isDragging
                ? 'bg-clinical-100 scale-110'
                : 'bg-clinical-50',
            ].join(' ')}>
              {isDragging
                ? <ImagePlus   className="w-8 h-8 text-clinical-500" />
                : <UploadCloud className="w-8 h-8 text-clinical-400" />
              }
            </div>

            <div>
              <p className="font-display font-semibold text-navy-800 text-base">
                {isDragging ? 'Release to upload' : 'Drop your X-ray image here'}
              </p>
              <p className="text-sm text-slate-400 mt-1">
                or{' '}
                <span className="text-clinical-600 font-medium hover:underline cursor-pointer">
                  browse files
                </span>
                {' '}from your computer
              </p>
            </div>

            <div className="flex gap-2 flex-wrap justify-center">
              {['JPEG', 'PNG', 'WebP', 'BMP'].map((fmt) => (
                <span
                  key={fmt}
                  className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 text-[11px] font-mono font-medium"
                >
                  {fmt}
                </span>
              ))}
              <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 text-[11px] font-mono font-medium">
                Max {MAX_SIZE_MB} MB
              </span>
            </div>
          </div>
        )}

        {/* Dragging border pulse */}
        {isDragging && (
          <div className="absolute inset-0 rounded-2xl ring-4 ring-clinical-400/40 animate-pulse pointer-events-none" />
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        onChange={handleInputChange}
        className="hidden"
        aria-hidden="true"
      />

      {/* ── Error message ─────────────────────────────── */}
      {displayError && (
        <div className="flex items-start gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl animate-slide-up">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{displayError}</p>
        </div>
      )}

      {/* ── Replace button (when image loaded) ────────── */}
      {preview && (
        <button
          onClick={() => inputRef.current?.click()}
          className="w-full py-2.5 rounded-xl border border-slate-200 text-sm text-slate-500 hover:text-clinical-600 hover:border-clinical-300 hover:bg-clinical-50 transition-all duration-200 font-medium"
        >
          Replace image
        </button>
      )}

    </div>
  )
}

export default UploadSection
