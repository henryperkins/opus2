// Main application component
import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Check backend health
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health/ready')
        if (!response.ok) throw new Error('API not responding')
        const data = await response.json()
        setHealth(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    checkHealth()
    // Recheck every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Productivity App</h1>
        <p className="version">v0.1.0 - Phase 1</p>
      </header>

      <main className="app-main">
        <section className="status-section">
          <h2>System Status</h2>

          {loading && <p className="loading">Checking system status...</p>}

          {error && (
            <div className="error">
              <p>❌ Connection Error: {error}</p>
              <p className="hint">Make sure the backend is running on port 8000</p>
            </div>
          )}

          {health && !error && (
            <div className="status-grid">
              <div className="status-item">
                <span className="label">API Status:</span>
                <span className={`value ${health.status === 'ready' ? 'success' : 'error'}`}>
                  {health.status === 'ready' ? '✅ Ready' : '❌ Not Ready'}
                </span>
              </div>

              <div className="status-item">
                <span className="label">Database:</span>
                <span className={`value ${health.database === 'ready' ? 'success' : 'error'}`}>
                  {health.database === 'ready' ? '✅ Connected' : '❌ Disconnected'}
                </span>
              </div>

              <div className="status-item">
                <span className="label">Last Check:</span>
                <span className="value">
                  {new Date(health.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          )}
        </section>

        <section className="info-section">
          <h2>Phase 1 Complete</h2>
          <ul className="feature-list">
            <li>✅ Project structure established</li>
            <li>✅ Database models (User, Project)</li>
            <li>✅ FastAPI backend with health checks</li>
            <li>✅ React frontend foundation</li>
            <li>✅ Docker development environment</li>
          </ul>

          <p className="next-phase">
            <strong>Next:</strong> Phase 2 will add authentication and user management
          </p>
        </section>
      </main>

      <footer className="app-footer">
        <p>AI Productivity App - Built for small teams</p>
      </footer>
    </div>
  )
}

export default App
