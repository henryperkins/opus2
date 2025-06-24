import React, { useState } from 'react';
import { useParams } from 'react-router-dom';

import RepositoryConnect from '../components/knowledge/RepositoryConnect';
import FileUpload from '../components/knowledge/FileUpload';
import KnowledgeContextPanel from '../components/knowledge/KnowledgeContextPanel';

// -----------------------------------------------------------------------------
// ProjectKnowledgePage – central hub for everything "Knowledge Base" related to
// a single project.  It lets the user:
//   • Connect a Git repository so the backend can ingest source code.
//   • Upload individual files.
//   • Run semantic search over the indexed knowledge using the context panel.
//
// NOTE:  The backend endpoints invoked by RepositoryConnect / FileUpload /
// KnowledgeContextPanel already exist in the code-base.  This page simply
// composes those components behind a minimal UI so navigating to
// /projects/:id/knowledge no longer yields a 404.
// -----------------------------------------------------------------------------

export default function ProjectKnowledgePage() {
  const { projectId } = useParams();

  const [query, setQuery] = useState('');

  return (
    <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-12">
      {/* Page header */}
      <header className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Knowledge Base
        </h1>

        <div className="flex-1 max-w-md ml-auto">
          <label htmlFor="kb-query" className="sr-only">
            Search knowledge base
          </label>
          <input
            id="kb-query"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search knowledge base…"
            className="w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </header>

      {/* Repository connection */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Connect a Repository</h2>
        <RepositoryConnect projectId={projectId} />
      </section>

      {/* File upload */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Upload Additional Files</h2>
        <FileUpload projectId={projectId} />
      </section>

      {/* Knowledge search results */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Search Results</h2>
        <KnowledgeContextPanel
          projectId={projectId}
          query={query}
          maxHeight="600px"
        />
      </section>
    </main>
  );
}
