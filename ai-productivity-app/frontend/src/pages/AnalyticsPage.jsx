/* AnalyticsPage.jsx – Project analytics dashboard
 *
 * First iteration:  
 *   • Fetches aggregated quality metrics from the backend  
 *   • Displays the numbers in a simple grid.  
 *   • Designed to be extended later with charts (e.g. recharts, chart.js).
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { analyticsAPI } from '../api/analytics';
import EmbeddingMetrics from '../components/analytics/EmbeddingMetrics';

export default function AnalyticsPage() {
  const { projectId } = useParams();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!projectId) return;

    const fetchMetrics = async () => {
      try {
        const data = await analyticsAPI.getQualityMetrics(projectId);
        setMetrics(data.data || data); // backend wraps inside {data, success}
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [projectId]);

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-6">
          Analytics Dashboard
        </h1>

        {/* Embedding Processing Metrics */}
        <div className="mb-8">
          <EmbeddingMetrics />
        </div>

        {/* Project Quality Metrics */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Project Quality Metrics
          </h2>

          {loading && <p className="text-gray-500 dark:text-gray-400">Loading metrics…</p>}
          {error && <p className="text-red-600 dark:text-red-400">{error}</p>}

          {metrics && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {Object.entries(metrics).map(([key, value]) => {
                // Skip embedding_performance since it's shown separately
                if (key === 'embedding_performance') return null;
                
                return (
                  <div
                    key={key}
                    className="bg-gray-50 dark:bg-gray-800 rounded-md p-4 border border-gray-200 dark:border-gray-700"
                  >
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 capitalize">
                      {key.replace(/_/g, ' ')}
                    </dt>
                    <dd className="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100">
                      {typeof value === 'number' ? value.toLocaleString() : 
                       Array.isArray(value) ? value.join(', ') : 
                       typeof value === 'string' ? value : 
                       JSON.stringify(value)}
                    </dd>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
  );
}
