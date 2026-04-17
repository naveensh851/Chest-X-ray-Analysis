import React from 'react'
import Home from './pages/Home'

/**
 * Root application component.
 * Currently single-page; can be extended with React Router.
 */
function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Home />
    </div>
  )
}

export default App
