import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import Home    from './pages/Home'
import Login   from './pages/Login'
import Reports from './pages/Reports'

/**
 * Root application component.
 * Sets up routing with react-router-dom v6 and wraps everything
 * in the AuthProvider for global auth state.
 *
 * Routes:
 *   /         → Home (protected)
 *   /login    → Login / Register
 *   /reports  → Saved reports (protected)
 *   *         → redirect to /
 */
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public route */}
          <Route path="/login" element={<Login />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Home />
              </PrivateRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <PrivateRoute>
                <Reports />
              </PrivateRoute>
            }
          />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
