import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import Header from '../components/common/Header';

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
              <button className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md">
                Create New Project
              </button>
              <button className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md">
                Search Code
              </button>
              <button className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md">
                View Timeline
              </button>
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
              <strong>Next:</strong> Phase 3 will add project management and file operations
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;