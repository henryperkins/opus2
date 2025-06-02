/* global fetch, setInterval, clearInterval */
import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import Header from '../components/common/Header';
import { Link } from 'react-router-dom';

function Dashboard() {
  const { user } = useAuth();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health/ready');
        if (!response.ok) throw new Error('API not responding');
        const data = await response.json();
        setHealth(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">Welcome back, {user?.username}!</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* System Status Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>

            {loading && (
              <div className="flex items-center text-gray-500">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                Checking status...
              </div>
            )}

            {error && (
              <div className="text-red-600">
                <p className="text-sm">Connection Error: {error}</p>
                <p className="text-xs text-gray-500 mt-1">Make sure the backend is running on port 8000</p>
              </div>
            )}

            {health && !error && (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">API Status:</span>
                  <span className={`text-sm font-medium ${health.status === 'ready' ? 'text-green-600' : 'text-red-600'}`}>
                    {health.status === 'ready' ? '✓ Ready' : '✗ Not Ready'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Database:</span>
                  <span className={`text-sm font-medium ${health.database === 'ready' ? 'text-green-600' : 'text-red-600'}`}>
                    {health.database === 'ready' ? '✓ Connected' : '✗ Disconnected'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Last Check:</span>
                  <span className="text-sm text-gray-900">
                    {new Date(health.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* User Info Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Account Info</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Username:</span>
                <span className="text-sm font-medium text-gray-900">{user?.username}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Email:</span>
                <span className="text-sm font-medium text-gray-900">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Status:</span>
                <span className="text-sm font-medium text-green-600">Active</span>
              </div>
            </div>
          </div>

          {/* Quick Actions Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
            <div className="space-y-2">
              <Link
                to="/projects"
                className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md block"
              >
                Manage Projects
              </Link>
              <Link
                to="/search"
                className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md block"
              >
                Search Code
              </Link>
              <Link
                to="/timeline"
                className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md block"
              >
                View Timeline
              </Link>
            </div>
          </div>
        </div>

        {/* Phase 2 Completion Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Phase 2 Complete ✅</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Infrastructure</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ Project structure established</li>
                <li>✓ Database models (User, Project)</li>
                <li>✓ FastAPI backend with health checks</li>
                <li>✓ React frontend foundation</li>
                <li>✓ Docker development environment</li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Authentication</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ User authentication & JWT tokens</li>
                <li>✓ Login/logout functionality</li>
                <li>✓ Protected routes</li>
                <li>✓ Session management</li>
                <li>✓ User preferences storage</li>
              </ul>
            </div>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-md">
            <p className="text-sm text-blue-800">
              <strong>Next:</strong> Phase 3 added project management – see below
            </p>
          </div>
        </div>

        {/* Phase 3 Completion Card */}
        <div className="bg-white rounded-lg shadow p-6 mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Phase 3 Complete ✅</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Project Management</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ Project CRUD with optimistic updates</li>
                <li>✓ Status tracking (Active / Archived / Completed)</li>
                <li>✓ Color & emoji customisation</li>
                <li>✓ Flexible tag & filter system</li>
                <li>✓ Pagination & responsive dashboard</li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Timeline & Search</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ Timeline event tracking for all changes</li>
                <li>✓ Search by status, tags, title and description</li>
                <li>✓ Role-based access enforcement</li>
                <li>✓ Extensive test coverage ({">"}90%)</li>
              </ul>
            </div>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-md">
            <p className="text-sm text-blue-800">
              <strong>Next:</strong> Phase 4 introduced code intelligence – see below
            </p>
          </div>
        </div>

        {/* Phase 4 Completion Card */}
        <div className="bg-white rounded-lg shadow p-6 mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Phase 4 Complete ✅</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Code Intelligence</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ File upload & language detection</li>
                <li>✓ Tree-sitter parsing & semantic chunking</li>
                <li>✓ Git repo integration with incremental diffing</li>
                <li>✓ OpenAI embeddings (async batches)</li>
                <li>✓ SQLite VSS vector store</li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Search & Visualisation</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ Hybrid semantic + keyword search</li>
                <li>✓ Dependency graph (D3.js)</li>
                <li>✓ Code snippet preview with highlighting</li>
                <li>✓ Backend endpoints & React Search UI</li>
                <li>✓ All modules ≤ 900 LOC</li>
              </ul>
            </div>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-md">
            <p className="text-sm text-blue-800">
              <strong>Next:</strong> Phase 5 (in progress) – real-time chat & AI assistance
            </p>
          </div>
        </div>

        {/* Phase 5 In-Progress Card */}
        <div className="bg-white rounded-lg shadow p-6 mt-8 border-l-4 border-yellow-400">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Phase 5 In&nbsp;Progress 🚧</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Realtime Chat</h3>
              <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                <li>WebSocket infrastructure &amp; connection manager</li>
                <li>Persistent ChatSession &amp; ChatMessage models</li>
                <li>Slash commands (e.g. <code>/explain</code>, <code>/generate-tests</code>)</li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">AI Assistance</h3>
              <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                <li>Streaming LLM responses (OpenAI)</li>
                <li>Secret redaction &amp; security scanning</li>
                <li>Split-pane chat / code interface</li>
              </ul>
            </div>
          </div>
          <div className="mt-4 p-3 bg-yellow-50 rounded-md">
            <p className="text-sm text-yellow-800">
              <strong>ETA:</strong> Chat UI and summarisation arriving shortly.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
