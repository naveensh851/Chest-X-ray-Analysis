import React, { createContext, useContext, useState, useCallback } from 'react'

/**
 * AuthContext — provides authentication state and helpers
 * throughout the React component tree.
 *
 * Keys stored in localStorage:
 *   xray_token  — JWT access token
 *   xray_user   — serialised { email } object
 */

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('xray_token'))
  const [user,  setUser]  = useState(() => {
    const raw = localStorage.getItem('xray_user')
    return raw ? JSON.parse(raw) : null
  })

  /** Call after a successful login/register response. */
  const saveAuth = useCallback((accessToken, email) => {
    localStorage.setItem('xray_token', accessToken)
    localStorage.setItem('xray_user', JSON.stringify({ email }))
    setToken(accessToken)
    setUser({ email })
  }, [])

  /** Clear auth state and storage. */
  const logout = useCallback(() => {
    localStorage.removeItem('xray_token')
    localStorage.removeItem('xray_user')
    setToken(null)
    setUser(null)
  }, [])

  const isAuthenticated = !!token

  return (
    <AuthContext.Provider value={{ token, user, isAuthenticated, saveAuth, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
