/* KnowledgeBasePage.jsx – CRUD browser for project knowledge entries
 *
 * Minimal first version: fetch list of entries and render table.  
 * Later iterations will add create/edit modal, search, pagination.
 */

import React from 'react';
import { useParams } from 'react-router-dom';
import useSWR from 'swr';
import knowledgeAPI from '../api/knowledge';

import SkeletonLines from '../components/common/SkeletonLines';
import ErrorBanner from '../components/common/ErrorBanner';

export default function KnowledgeBasePage() {
  const { projectId } = useParams();
  const { data: entries = [], error, isLoading } = useSWR(
    projectId ? ['kb', projectId] : null,
    ([, id]) => knowledgeAPI.semanticSearch(id, '*', { limit: 100 }),
    {
      suspense: false,
      revalidateOnFocus: false,
      fallbackData: [],
    },
  );

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Knowledge Base</h1>

        {isLoading && <SkeletonLines rows={6} />}
        {error && <ErrorBanner>{error.message || String(error)}</ErrorBanner>}

        {entries.length > 0 && (
          <div className="overflow-x-auto rounded-lg shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 bg-white hidden sm:table">
              <caption className="sr-only">Knowledge entries</caption>
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {entries.map((e) => (
                  <tr
                    key={e.id || e.entry_id}
                    tabIndex={0}
                    role="link"
                    onClick={() => e.url && window.open(e.url, '_blank')}
                    className="hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-brand-primary-400 cursor-pointer"
                  >
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

        {/* Mobile cards */}
        {entries.length > 0 && (
          <div className="sm:hidden space-y-2">
            {entries.map((e) => (
              <div
                key={e.id || e.entry_id}
                className="card card-hover p-4 cursor-pointer"
                role="link"
                onClick={() => e.url && window.open(e.url, '_blank')}
              >
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                  {e.title || e.path || '—'}
                </h3>
                <p className="text-xs mt-1 text-gray-500 dark:text-gray-400">
                  {e.source || e.repo || '—'}
                </p>
                <p className="mt-2 text-brand-primary-600 dark:text-brand-primary-400">
                  {e.score ? e.score.toFixed(2) : '—'}
                </p>
              </div>
            ))}
          </div>
        )}

        {!isLoading && entries.length === 0 && !error && (
          <div className="card card-hover p-6 text-center text-gray-500 dark:text-gray-400">
            <p>No knowledge entries yet.</p>
            <p className="mt-2 text-sm">Import docs or run code analysis to populate.</p>
          </div>
        )}
      </main>
  );
}
