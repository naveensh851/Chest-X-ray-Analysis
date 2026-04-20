import React, { useState, useRef, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Activity, Shield, ClipboardList, LogOut, ChevronDown, User,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

/**
 * Navbar — top application bar with branding, navigation and user menu.
 * Shows auth-aware controls: user avatar + dropdown when logged in.
 */
function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  /** Get initials from email */
  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : 'DR'

  return (
    <header className="sticky top-0 z-50 w-full">
      {/* Frosted glass bar */}
      <div className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* ── Brand ─────────────────────────────────── */}
            <Link to="/" className="flex items-center gap-3 no-underline">
              {/* Icon badge */}
              <div className="relative flex-shrink-0">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-clinical-500 to-navy-700 flex items-center justify-center shadow-glow">
                  <Activity className="w-5 h-5 text-white" strokeWidth={2.2} />
                </div>
                {/* Live pulse dot */}
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 border-2 border-white rounded-full animate-pulse-soft" />
              </div>

              <div className="hidden sm:block">
                <p className="font-display font-bold text-navy-900 leading-tight text-[15px]">
                  AI X-ray Diagnosis
                </p>
                <p className="text-[10px] font-medium text-clinical-500 tracking-widest uppercase">
                  Diagnostic System
                </p>
              </div>

              {/* Mobile compact title */}
              <span className="sm:hidden font-display font-bold text-navy-900 text-sm">
                XrayDx
              </span>
            </Link>

            {/* ── Center badge ──────────────────────────── */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-full">
              <Shield className="w-3.5 h-3.5 text-emerald-600" />
              <span className="text-xs font-medium text-emerald-700">
                Get Precise Reports
              </span>
            </div>

            {/* ── Right utilities ───────────────────────── */}
            <div className="flex items-center gap-1">
              {isAuthenticated ? (
                <>
                  {/* Reports link */}
                  <Link
                    to="/reports"
                    id="nav-reports"
                    className="hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-lg text-slate-500 hover:text-clinical-600 hover:bg-clinical-50 transition-colors text-sm font-medium"
                  >
                    <ClipboardList className="w-4 h-4" />
                    Reports
                  </Link>

                  {/* User dropdown */}
                  <div className="relative ml-1" ref={menuRef}>
                    <button
                      id="nav-user-menu"
                      aria-label="User menu"
                      onClick={() => setOpen(v => !v)}
                      className="flex items-center gap-2 pl-2 pr-1.5 py-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                    >
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-navy-400 to-clinical-600 flex items-center justify-center text-white text-xs font-bold font-display shadow-sm">
                        {initials}
                      </div>
                      <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
                    </button>

                    {/* Dropdown */}
                    {open && (
                      <div className="absolute right-0 mt-2 w-56 bg-white border border-slate-200 rounded-2xl shadow-xl py-1.5 animate-slide-up z-50">
                        <div className="px-4 py-2.5 border-b border-slate-100">
                          <div className="flex items-center gap-2">
                            <User className="w-3.5 h-3.5 text-slate-400" />
                            <p className="text-xs font-medium text-slate-800 truncate">{user?.email}</p>
                          </div>
                        </div>

                        <Link
                          to="/reports"
                          id="dropdown-reports"
                          onClick={() => setOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-600 hover:bg-clinical-50 hover:text-clinical-700 transition-colors"
                        >
                          <ClipboardList className="w-4 h-4" />
                          My Reports
                        </Link>

                        <button
                          id="btn-logout"
                          onClick={handleLogout}
                          className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors"
                        >
                          <LogOut className="w-4 h-4" />
                          Sign Out
                        </button>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-clinical-600 text-white text-sm font-semibold hover:bg-clinical-700 transition-colors"
                >
                  Sign In
                </Link>
              )}
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
