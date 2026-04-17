import React from 'react'
import { Activity, Shield, Bell, HelpCircle } from 'lucide-react'

/**
 * Navbar — top application bar with branding and utility icons.
 * Uses a frosted-glass style on scroll using CSS backdrop-filter.
 */
function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full">
      {/* Frosted glass bar */}
      <div className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* ── Brand ─────────────────────────────────── */}
            <div className="flex items-center gap-3">
              {/* Icon badge */}
              <div className="relative flex-shrink-0">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-clinical-500 to-navy-700 flex items-center justify-center shadow-glow">
                  <Activity className="w-5 h-5 text-white" strokeWidth={2.2} />
                </div>
                {/* Live pulse dot */}
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 border-2 border-white rounded-full animate-pulse-soft" />
              </div>

              <div className="hidden sm:block">
                <h1 className="font-display font-bold text-navy-900 leading-tight text-[15px]">
                  AI X-ray Diagnosis
                </h1>
                <p className="text-[10px] font-medium text-clinical-500 tracking-widest uppercase">
                  Diagnostic System
                </p>
              </div>

              {/* Mobile compact title */}
              <span className="sm:hidden font-display font-bold text-navy-900 text-sm">
                XrayDx
              </span>
            </div>

            {/* ── Center badge ──────────────────────────── */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-full">
              <Shield className="w-3.5 h-3.5 text-emerald-600" />
              <span className="text-xs font-medium text-emerald-700">
                HIPAA Compliant · Demo Mode
              </span>
            </div>

            {/* ── Right utilities ───────────────────────── */}
            <div className="flex items-center gap-1">
              <button
                aria-label="Notifications"
                className="p-2 rounded-lg text-slate-400 hover:text-clinical-600 hover:bg-clinical-50 transition-colors"
              >
                <Bell className="w-4.5 h-4.5" />
              </button>
              <button
                aria-label="Help"
                className="p-2 rounded-lg text-slate-400 hover:text-clinical-600 hover:bg-clinical-50 transition-colors"
              >
                <HelpCircle className="w-4.5 h-4.5" />
              </button>

              {/* User avatar placeholder */}
              <div className="ml-2 w-8 h-8 rounded-full bg-gradient-to-br from-navy-400 to-clinical-600 flex items-center justify-center text-white text-xs font-bold font-display cursor-pointer hover:opacity-90 transition-opacity shadow-sm">
                DR
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* Subtle gradient line below navbar */}
      <div className="h-px bg-gradient-to-r from-transparent via-clinical-400/40 to-transparent" />
    </header>
  )
}

export default Navbar
