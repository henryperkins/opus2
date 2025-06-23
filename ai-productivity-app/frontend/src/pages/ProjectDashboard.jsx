// frontend/src/pages/ProjectDashboard.jsx
// -----------------------------------------------------------------------------
// Project Dashboard – lists all projects with filters, stats and quick actions.
// Each ProjectCard now links directly to the full project overview page.
// -----------------------------------------------------------------------------

import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

// Components & hooks
import ProjectCard from '../components/projects/ProjectCard';
import CreateProjectModal from '../components/projects/CreateProjectModal';
import Timeline from '../components/projects/Timeline';
import ProjectFilters from '../components/projects/ProjectFilters';
import LoadingSpinner from '../components/common/LoadingSpinner';

import useProjectStore from '../stores/projectStore';
import { useAuth } from '../hooks/useAuth';

export default function ProjectDashboard() {
  const navigate = useNavigate();

  // ---------------------------------------------------------------------------
  // Global data via Zustand store
  // ---------------------------------------------------------------------------
  const {
    projects,
    totalProjects,
    fetchProjects,
    loading,
    error,
    filters,
    setFilters,
    setPage,
    archiveProject,
    unarchiveProject,
    deleteProject,
  } = useProjectStore();

  // ---------------------------------------------------------------------------
  // Local UI state
  // ---------------------------------------------------------------------------
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [view, setView] = useState('grid'); // 'grid' | 'timeline'

  // ---------------------------------------------------------------------------
  // Authentication – only fetch once user is known
  // ---------------------------------------------------------------------------
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && user) {
      fetchProjects();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, filters]);

  // ---------------------------------------------------------------------------
  // Action handlers
  // ---------------------------------------------------------------------------
  const handleArchive = async (projectId) => {
    try {
      await archiveProject(projectId);
      fetchProjects();
    } catch (err) {
      /* eslint-disable no-console */
      console.error('Failed to archive project:', err);
    }
  };

  const handleUnarchive = async (projectId) => {
    try {
      await unarchiveProject(projectId);
      fetchProjects();
    } catch (err) {
      console.error('Failed to unarchive project:', err);
    }
  };

  const handleDelete = async (projectId) => {
    if (window.confirm('Are you sure you want to delete this project?')) {
      try {
        await deleteProject(projectId);
        fetchProjects();
      } catch (err) {
        console.error('Failed to delete project:', err);
      }
    }
  };

  const handleProjectCreated = () => {
    setShowCreateModal(false);
    fetchProjects();
  };

  const handleFilterChange = (newFilters) => setFilters(newFilters);
  const handlePageChange = (newPage) => setPage(newPage);

  // Derived counts
  const activeProjects = projects.filter((p) => p.status === 'active');
  const archivedProjects = projects.filter((p) => p.status === 'archived');

  const totalPages = Math.ceil(totalProjects / filters.per_page);

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------
  const renderProjectGrid = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {projects.map((project) => (
        <div key={project.id} className="relative">
          {/* Clicking the whole card navigates to the overview page */}
          <Link to={`/projects/${project.id}`} className="block group">
            <ProjectCard project={project} />
          </Link>

          {/* Quick-action buttons overlay (chat/archive etc.) */}
          <div className="absolute top-2 right-2 flex space-x-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/projects/${project.id}/chat`, { state: { project } });
              }}
              className="p-1 bg-white rounded shadow hover:bg-gray-100"
              title="Open Chat"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </button>

            {project.status === 'active' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleArchive(project.id);
                }}
                className="p-1 bg-white rounded shadow hover:bg-gray-100"
                title="Archive"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                  />
                </svg>
              </button>
            )}

            {project.status === 'archived' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleUnarchive(project.id);
                }}
                className="p-1 bg-white rounded shadow hover:bg-gray-100"
                title="Unarchive"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 4v16h16V4H4zm4 4h8v2H8V8zm0 4h8v6H8v-6z"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  // ---------------------------------------------------------------------------
  // Main render
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen gradient-bg">

      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Page header with quick stats */}
        <div className="flex justify-between items-center mb-8 animate-fade-in">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent dark:from-gray-100 dark:to-gray-300">
              Project Dashboard
            </h1>

            <div className="flex items-center mt-2 space-x-4 text-sm">
              <div className="flex items-center text-gray-600 dark:text-gray-400">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
                {totalProjects} project{totalProjects !== 1 ? 's' : ''}
              </div>
              <div className="flex items-center text-green-600 dark:text-green-400">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
                {activeProjects.length} active
              </div>
              <div className="flex items-center text-gray-500">
                <div className="w-2 h-2 bg-gray-400 rounded-full mr-2" />
                {archivedProjects.length} archived
              </div>
            </div>
          </div>

          {/* Create new project & view toggle */}
          <div className="flex items-center space-x-4">
            <div className="flex bg-gray-200 rounded-lg p-1">
              <button
                onClick={() => setView('grid')}
                className={`px-3 py-1 rounded ${
                  view === 'grid' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
                }`}
                aria-label="Grid view"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                  />
                </svg>
              </button>
              <button
                onClick={() => setView('timeline')}
                className={`px-3 py-1 rounded ${
                  view === 'timeline' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
                }`}
                aria-label="Timeline view"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </button>
            </div>

            <button
              onClick={() => setShowCreateModal(true)}
              className="btn btn-primary animate-bounce-in"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              New Project
            </button>
          </div>
        </div>

        {/* Filters */}
        <ProjectFilters filters={filters} onChange={handleFilterChange} />

        {/* Main content */}
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner label="Loading projects…" showLabel />
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
          </div>
        ) : view === 'grid' ? (
          renderProjectGrid()
        ) : (
          <Timeline projectId={selectedProject?.id} />
        )}

        {/* Pagination – placeholder (implement when backend supports) */}
        {/* Example:
        <Pagination
          page={filters.page}
          pageCount={totalPages}
          onPageChange={handlePageChange}
        />
        */}
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <CreateProjectModal onClose={() => setShowCreateModal(false)} onCreated={handleProjectCreated} />
      )}
    </div>
  );
}
