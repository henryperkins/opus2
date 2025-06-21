/* KnowledgeBasePage.jsx – CRUD browser for project knowledge entries
 *
 * Minimal first version: fetch list of entries and render table.  
 * Later iterations will add create/edit modal, search, pagination.
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { knowledgeAPI } from '../api/knowledge';

export default function KnowledgeBasePage() {
  const { projectId } = useParams();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!projectId) return;

    const fetchEntries = async () => {
      try {
        // Temporary – backend path mismatch will be fixed separately
        const data = await knowledgeAPI.semanticSearch(projectId, '*', { limit: 100 });
        setEntries(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchEntries();
  }, [projectId]);

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Knowledge Base</h1>

        {loading && <p className="text-gray-500">Loading…</p>}
        {error && <p className="text-red-600">{error}</p>}

        {entries.length > 0 && (
          <div className="overflow-x-auto rounded-lg shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 bg-white">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {entries.map((e) => (
                  <tr key={e.id || e.entry_id}>
                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                      {e.title || e.path || '—'}
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                      {e.source || e.repo || '—'}
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                      {e.score ? e.score.toFixed(2) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && entries.length === 0 && !error && (
          <p className="text-gray-400">No knowledge entries found for this project.</p>
        )}
      </main>
  );
}
