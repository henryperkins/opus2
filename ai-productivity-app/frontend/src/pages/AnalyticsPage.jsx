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
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          Analytics Dashboard
        </h1>

        {loading && <p className="text-gray-500">Loading metrics…</p>}
        {error && <p className="text-red-600">{error}</p>}

        {metrics && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Object.entries(metrics).map(([key, value]) => (
              <div
                key={key}
                className="bg-white shadow-sm rounded-md p-4 border border-gray-100"
              >
                <dt className="text-sm font-medium text-gray-500 capitalize">
                  {key.replace(/_/g, ' ')}
                </dt>
                <dd className="mt-1 text-2xl font-semibold text-gray-900">
                  {typeof value === 'number' ? value.toLocaleString() : value}
                </dd>
              </div>
            ))}
          </div>
        )}
      </main>
  );
}
