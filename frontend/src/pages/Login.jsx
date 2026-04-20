import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Activity, Eye, EyeOff, Zap, Lock, Mail, UserPlus, LogIn } from 'lucide-react'
import { loginUser, registerUser } from '../services/api'
import { useAuth } from '../context/AuthContext'

/**
 * Login — allows existing users to sign in or new users to register.
 * Tab-based UI: "Sign In" / "Create Account".
 */
function Login() {
  const navigate       = useNavigate()
  const { saveAuth }   = useAuth()

  const [tab,       setTab]       = useState('login')    // 'login' | 'register'
  const [email,     setEmail]     = useState('')
  const [password,  setPassword]  = useState('')
  const [showPass,  setShowPass]  = useState(false)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)

  const isLogin = tab === 'login'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!email || !password) {
      setError('Please fill in both fields.')
      return
    }
    if (password.length < 4) {
      setError('Password must be at least 4 characters.')
      return
    }

    setLoading(true)
    try {
      const data = isLogin
        ? await loginUser(email, password)
        : await registerUser(email, password)

      saveAuth(data.access_token, email)
      navigate('/')
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        (err.request ? 'Cannot reach server. Is the backend running?' : 'Something went wrong.')
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-slate-900 overflow-hidden relative">

      {/* ── Left decorative panel ─────────────────────────── */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        {/* Animated gradient blob */}
        <div className="absolute inset-0 bg-gradient-to-br from-clinical-900 via-navy-900 to-slate-900" />
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-clinical-600/20 blur-3xl animate-pulse-soft" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[400px] h-[400px] rounded-full bg-navy-500/20 blur-3xl animate-pulse-soft" style={{ animationDelay: '1s' }} />

        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-clinical-500 to-navy-600 flex items-center justify-center shadow-glow">
            <Activity className="w-5 h-5 text-white" strokeWidth={2.2} />
          </div>
          <div>
            <p className="font-display font-bold text-white text-base leading-tight">AI X-ray Diagnosis</p>
            <p className="text-[10px] text-clinical-400 tracking-widest uppercase">Diagnostic System</p>
          </div>
        </div>

        <div className="relative z-10 space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 rounded-full text-xs font-medium text-clinical-300 border border-white/10">
            <Zap className="w-3.5 h-3.5" />
            Powered by Deep Learning
          </div>
          <h2 className="font-display font-extrabold text-4xl text-white leading-tight">
            AI-Powered<br />
            <span className="text-clinical-400">Chest X-ray</span><br />
            Analysis
          </h2>
          <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
            Upload a chest X-ray and receive an instant AI-powered analysis with
            disease prediction and a preliminary radiology report — all securely
            saved to your personal dashboard.
          </p>

          {/* Feature chips */}
          <div className="flex flex-wrap gap-2 pt-2">
            {['94.2% Accuracy', '14+ Diseases', 'Secure Storage', 'Instant Results'].map(f => (
              <span
                key={f}
                className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300"
              >
                {f}
              </span>
            ))}
          </div>
        </div>

        <div className="relative z-10 text-xs text-slate-600">
          © 2024 AI X-ray Diagnosis System · Research use only
        </div>
      </div>

      {/* ── Right form panel ──────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 relative">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 to-slate-800" />

        <div className="relative z-10 w-full max-w-md">

          {/* Mobile branding */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-clinical-500 to-navy-600 flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" strokeWidth={2.2} />
            </div>
            <p className="font-display font-bold text-white">AI X-ray Diagnosis</p>
          </div>

          {/* Card */}
          <div className="bg-slate-800/80 backdrop-blur-xl border border-slate-700/60 rounded-3xl p-8 shadow-2xl">

            {/* Tab switcher */}
            <div className="flex rounded-2xl bg-slate-900/60 p-1 mb-8">
              {[
                { id: 'login',    label: 'Sign In',        icon: LogIn   },
                { id: 'register', label: 'Create Account', icon: UserPlus },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  id={`tab-${id}`}
                  onClick={() => { setTab(id); setError(null) }}
                  className={[
                    'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300',
                    tab === id
                      ? 'bg-gradient-to-r from-clinical-600 to-navy-700 text-white shadow-lg'
                      : 'text-slate-400 hover:text-slate-200',
                  ].join(' ')}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            <div className="mb-6">
              <h1 className="font-display font-bold text-white text-2xl">
                {isLogin ? 'Welcome back' : 'Create your account'}
              </h1>
              <p className="text-slate-400 text-sm mt-1">
                {isLogin
                  ? 'Sign in to access your X-ray reports.'
                  : 'Start analysing X-rays and saving your reports.'}
              </p>
            </div>

            {/* Error banner */}
            {error && (
              <div className="mb-5 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>

              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium text-slate-300">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="doctor@hospital.com"
                    className="w-full pl-10 pr-4 py-3 bg-slate-900/60 border border-slate-700 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:ring-2 focus:ring-clinical-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium text-slate-300">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                  <input
                    id="password"
                    type={showPass ? 'text' : 'password'}
                    autoComplete={isLogin ? 'current-password' : 'new-password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-11 py-3 bg-slate-900/60 border border-slate-700 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:ring-2 focus:ring-clinical-500 focus:border-transparent transition-all"
                  />
                  <button
                    type="button"
                    aria-label={showPass ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPass(v => !v)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                id="btn-submit"
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl font-display font-semibold text-sm bg-gradient-to-r from-clinical-600 to-navy-700 text-white shadow-lg hover:shadow-glow hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-300"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    {isLogin ? 'Signing in…' : 'Creating account…'}
                  </>
                ) : (
                  <>
                    {isLogin ? <LogIn className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
                    {isLogin ? 'Sign In' : 'Create Account'}
                  </>
                )}
              </button>
            </form>

            {/* Divider hint */}
            <p className="text-center text-xs text-slate-500 mt-6">
              {isLogin ? "Don't have an account? " : 'Already have an account? '}
              <button
                onClick={() => { setTab(isLogin ? 'register' : 'login'); setError(null) }}
                className="text-clinical-400 hover:text-clinical-300 font-medium transition-colors"
              >
                {isLogin ? 'Create one' : 'Sign in'}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login
