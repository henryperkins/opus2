/* eslint-env browser */
import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Link } from 'react-router-dom';

function Dashboard() {
  const { user } = useAuth();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        // Use absolute backend URL so that local development (without Vite
        // proxy) and Docker both work.  We fall back to localhost when the
        // VITE env variable is absent.
        // Determine the backend base URL.
        //
        // 1. If the VITE_API_URL environment variable is provided *and* the
        //    site is not served over HTTPS (to avoid mixed-content warnings),
        //    use that value.  When developers forget to include the protocol
        //    ("localhost:8000" instead of "http://localhost:8000") we prefix
        //    it with "http://" so that the resulting URL is valid.
        // 2. Otherwise fall back to:
        //    • an empty string when running on HTTPS (so the request is
        //      relative to the current origin and keeps the secure scheme),
        //    • or the conventional FastAPI dev port 8000 for HTTP.

        const envUrl = import.meta.env.VITE_API_URL;
        const shouldUseEnv = envUrl && window.location.protocol !== 'https:';

        const base = shouldUseEnv
          ? (envUrl.startsWith('http://') || envUrl.startsWith('https://')
              ? envUrl
              : `http://${envUrl}`)
          : (window.location.protocol === 'https:' ? '' : 'http://localhost:8000');
        const response = await fetch(`${base}/health/ready`, {
          credentials: 'include',
        });
        if (!response.ok) throw new Error('API not responding');
        const data = await response.json();

        // Surface DB connection issues separately so users know next steps
        if (data.database && data.database !== 'ready') {
          setError('Database connection failed. Please ensure the database service is running.');
        } else {
          setError(null);
        }

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
    <div className="min-h-screen gradient-bg">

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-8 animate-fade-in">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent dark:from-gray-100 dark:to-gray-300">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2 text-lg">Welcome back, <span className="font-semibold text-blue-600 dark:text-blue-400">{user?.username}</span>!</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* System Status Card */}
          <div className="card card-hover p-6 animate-slide-in">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
              <div className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></div>
              System Status
            </h2>

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
          <div className="card card-hover p-6 animate-slide-in" style={{animationDelay: '0.1s'}}>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mr-2">
                <span className="text-white text-sm font-bold">{user?.username?.charAt(0).toUpperCase()}</span>
              </div>
              Account Info
            </h2>
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
          <div className="card card-hover p-6 animate-slide-in" style={{animationDelay: '0.2s'}}>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
              <svg className="w-5 h-5 text-blue-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Quick Actions
            </h2>
            <div className="space-y-3">
              <Link
                to="/projects"
                className="group flex items-center w-full text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-700 dark:hover:text-blue-300 rounded-lg transition-all duration-200 border border-transparent hover:border-blue-200 dark:hover:border-blue-700"
              >
                <svg className="w-5 h-5 mr-3 text-gray-400 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                Manage Projects
              </Link>
              <Link
                to="/search"
                className="group flex items-center w-full text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-700 dark:hover:text-blue-300 rounded-lg transition-all duration-200 border border-transparent hover:border-blue-200 dark:hover:border-blue-700"
              >
                <svg className="w-5 h-5 mr-3 text-gray-400 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Search Code
              </Link>
              <Link
                to="/timeline"
                className="group flex items-center w-full text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-700 dark:hover:text-blue-300 rounded-lg transition-all duration-200 border border-transparent hover:border-blue-200 dark:hover:border-blue-700"
              >
                <svg className="w-5 h-5 mr-3 text-gray-400 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
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
{/* Phase 6 Completion Card */}
        <div className="bg-white rounded-lg shadow p-6 mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Phase 6 Complete ✅
          </h2>
        </div>

        {/* Phase 7 Completion Card */}
        <div className="bg-white rounded-lg shadow p-6 mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Phase 7 Complete ✅
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Project Dashboard
              </h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ Enhanced project management UI</li>
                <li>✓ Grid and timeline views</li>
                <li>✓ Quick stats and filtering</li>
                <li>✓ Project details sidebar</li>
                <li>✓ Integrated file explorer</li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Code Chat Interface
              </h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ Split-pane chat/code editor</li>
                <li>✓ Monaco editor integration</li>
                <li>✓ File browser sidebar</li>
                <li>✓ Code snippet handling</li>
                <li>✓ Advanced search with history</li>
              </ul>
            </div>
          </div>
          <div className="mt-4 p-3 bg-green-50 rounded-md">
            <p className="text-sm text-green-800">
              <strong>Complete:</strong> All frontend features implemented and
              integrated
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
