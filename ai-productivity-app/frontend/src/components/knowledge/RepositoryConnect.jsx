// Git repository connection interface with branch selection and sync status
import React, { useState } from 'react';
// Adjusted import path to existing API module. Previously pointed to a non-existent
// '../../api/repositories' file which broke the Vite build.
import { repositoryAPI } from '../../api/github';

export default function RepositoryConnect({ projectId, onSuccess }) {
  const [formData, setFormData] = useState({
    repo_url: '',
    branch: 'main'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await repositoryAPI.connectRepository(projectId, formData);
      onSuccess?.(result);
      setFormData({ repo_url: '', branch: 'main' });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to connect repository');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="repository-connect">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="repo_url" className="block text-sm font-medium text-gray-700">
            Repository URL
          </label>
          <input
            type="url"
            id="repo_url"
            name="repo_url"
            value={formData.repo_url}
            onChange={handleChange}
            placeholder="https://github.com/user/repo.git"
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
          <p className="mt-1 text-xs text-gray-500">
            HTTPS URL for public repositories or SSH for private ones
          </p>
        </div>

        <div>
          <label htmlFor="branch" className="block text-sm font-medium text-gray-700">
            Branch
          </label>
          <input
            type="text"
            id="branch"
            name="branch"
            value={formData.branch}
            onChange={handleChange}
            placeholder="main"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {loading ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Connecting...
            </>
          ) : (
            'Connect Repository'
          )}
        </button>
      </form>
    </div>
  );
}
