import React from 'react'

/**
 * Loader — animated scanning overlay shown while the API processes the image.
 * Combines a rotating ring with a scan-line animation over the X-ray preview.
 *
 * @param {string} [message] - Optional status message to display
 */
function Loader({ message = 'Analyzing X-ray…' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-10 animate-fade-in">

      {/* ── Animated ring ─────────────────────────────── */}
      <div className="relative w-20 h-20">
        {/* Outer slow-spin ring */}
        <div className="absolute inset-0 rounded-full border-4 border-clinical-100" />
        <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-clinical-500 border-r-clinical-300 animate-spin" />

        {/* Inner fast-spin ring */}
        <div
          className="absolute inset-2 rounded-full border-4 border-transparent border-b-navy-600 animate-spin"
          style={{ animationDuration: '0.8s', animationDirection: 'reverse' }}
        />

        {/* Center pulse dot */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full bg-clinical-500 animate-pulse" />
        </div>
      </div>

      {/* ── Status text ───────────────────────────────── */}
      <div className="text-center space-y-2">
        <p className="font-display font-semibold text-navy-800 text-sm">{message}</p>

        {/* Dot pulse indicator */}
        <div className="dot-pulse flex items-center justify-center gap-1.5">
          <span /><span /><span />
        </div>

        {/* Steps list */}
        <ul className="text-xs text-slate-400 space-y-0.5 mt-3">
          {['Preprocessing image…', 'Running inference model…', 'Generating report…'].map((step) => (
            <li key={step} className="flex items-center gap-1.5 justify-center">
              <span className="w-1 h-1 rounded-full bg-clinical-300 inline-block" />
              {step}
            </li>
          ))}
        </ul>
      </div>

    </div>
  )
}

export default Loader
