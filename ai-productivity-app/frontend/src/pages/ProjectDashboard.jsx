// frontend/src/pages/ProjectDashboard.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/common/Header';
import ProjectCard from '../components/projects/ProjectCard';
import CreateProjectModal from '../components/projects/CreateProjectModal';
import Timeline from '../components/projects/Timeline';
import ProjectFilters from '../components/projects/ProjectFilters';
import useProjectStore from '../stores/projectStore';
import { useAuth } from '../hooks/useAuth';

export default function ProjectDashboard() {
    const navigate = useNavigate();
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
        deleteProject
    } = useProjectStore();

    const [showCreateModal, setShowCreateModal] = useState(false);
    const [selectedProject, setSelectedProject] = useState(null);
    const [view, setView] = useState('grid'); // grid or timeline
    const { user, loading: authLoading } = useAuth();

    // Only fetch projects after user is known and auth check is done
    useEffect(() => {
        if (!authLoading && user) {
            fetchProjects();
        }
    }, [filters, fetchProjects, authLoading, user]);

    const handleProjectClick = (project) => {
        setSelectedProject(project);
    };

    const handleArchive = async (projectId) => {
        try {
            await archiveProject(projectId);
            fetchProjects();
        } catch (err) {
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

    const handleFilterChange = (newFilters) => {
        setFilters(newFilters);
    };

    const handlePageChange = (newPage) => {
        setPage(newPage);
    };

    const handleProjectCreated = () => {
        setShowCreateModal(false);
        fetchProjects();
    };

    const activeProjects = projects.filter(p => p.status === 'active');
    const archivedProjects = projects.filter(p => p.status === 'archived');

    const totalPages = Math.ceil(totalProjects / filters.per_page);

    return (
        <div className="min-h-screen gradient-bg">
            <Header />

            <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
                {/* Header */}
                <div className="flex justify-between items-center mb-8 animate-fade-in">
                    <div>
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent dark:from-gray-100 dark:to-gray-300">Project Dashboard</h1>
                        <div className="flex items-center mt-2 space-x-4 text-sm">
                            <div className="flex items-center text-gray-600 dark:text-gray-400">
                                <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                                {totalProjects} project{totalProjects !== 1 ? 's' : ''}
                            </div>
                            <div className="flex items-center text-green-600 dark:text-green-400">
                                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                                {activeProjects.length} active
                            </div>
                            <div className="flex items-center text-gray-500">
                                <div className="w-2 h-2 bg-gray-400 rounded-full mr-2"></div>
                                {archivedProjects.length} archived
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center space-x-4">
                        {/* View Toggle */}
                        <div className="flex bg-gray-200 rounded-lg p-1">
                            <button
                                onClick={() => setView('grid')}
                                className={`px-3 py-1 rounded ${view === 'grid'
                                        ? 'bg-white text-gray-900 shadow-sm'
                                        : 'text-gray-600'
                                    }`}
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                                </svg>
                            </button>
                            <button
                                onClick={() => setView('timeline')}
                                className={`px-3 py-1 rounded ${view === 'timeline'
                                        ? 'bg-white text-gray-900 shadow-sm'
                                        : 'text-gray-600'
                                    }`}
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
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

                {/* Quick Stats */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                    <div className="card card-hover p-6 animate-slide-in">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Projects</p>
                                <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{totalProjects}</p>
                            </div>
                            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                </svg>
                            </div>
                        </div>
                    </div>
                    <div className="card card-hover p-6 animate-slide-in" style={{animationDelay: '0.1s'}}>
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Active</p>
                                <p className="text-3xl font-bold text-green-600">{activeProjects.length}</p>
                            </div>
                            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                        </div>
                    </div>
                    <div className="card card-hover p-6 animate-slide-in" style={{animationDelay: '0.2s'}}>
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Archived</p>
                                <p className="text-3xl font-bold text-gray-500">{archivedProjects.length}</p>
                            </div>
                            <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                                </svg>
                            </div>
                        </div>
                    </div>
                    <div className="card card-hover p-6 animate-slide-in" style={{animationDelay: '0.3s'}}>
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">This Week</p>
                                <p className="text-3xl font-bold text-blue-600">
                                    {projects.filter(p => {
                                        const createdAt = new Date(p.created_at);
                                        const weekAgo = new Date();
                                        weekAgo.setDate(weekAgo.getDate() - 7);
                                        return createdAt > weekAgo;
                                    }).length}
                                </p>
                            </div>
                            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex gap-8">
                    <div className="flex-1">
                        {loading ? (
                            <div className="flex justify-center items-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                <span className="ml-3 text-gray-600">Loading projects...</span>
                            </div>
                        ) : error ? (
                            <div className="bg-red-50 border border-red-200 rounded-md p-4">
                                <p className="text-red-800">{error}</p>
                            </div>
                        ) : view === 'grid' ? (
                            <>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {projects.map(project => (
                                    <div key={project.id} className="relative">
                                        <ProjectCard
                                            project={project}
                                            onClick={() => handleProjectClick(project)}
                                        />
                                        <div className="absolute top-2 right-2 flex space-x-1">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    navigate(`/projects/${project.id}/chat`, { state: { project } });
                                                }}
                                                className="p-1 bg-white rounded shadow hover:bg-gray-100"
                                                title="Open Chat"
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
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
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
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
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v16h16V4H4zm4 4h8v2H8V8zm0 4h8v6H8v-6z" />
                                                    </svg>
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="flex justify-center items-center space-x-2 mt-6">
                                    <button
                                        onClick={() => handlePageChange(filters.page - 1)}
                                        disabled={filters.page <= 1}
                                        className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Previous
                                    </button>
                                    <span className="px-3 py-2 text-sm text-gray-700">
                                        Page {filters.page} of {totalPages}
                                    </span>
                                    <button
                                        onClick={() => handlePageChange(filters.page + 1)}
                                        disabled={filters.page >= totalPages}
                                        className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Next
                                    </button>
                                </div>
                            )}
                            </>
                        ) : (
                            <Timeline projectId={selectedProject?.id} />
                        )}
                    </div>

                    {/* Project Details Sidebar */}
                    {selectedProject && view === 'grid' && (
                        <div className="w-80 bg-white rounded-lg shadow p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-semibold text-gray-900">Project Details</h3>
                                <button
                                    onClick={() => setSelectedProject(null)}
                                    className="text-gray-400 hover:text-gray-600"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center">
                                    <span className="text-2xl mr-2">{selectedProject.emoji}</span>
                                    <h4 className="text-xl font-medium">{selectedProject.title}</h4>
                                </div>

                                <p className="text-gray-600">{selectedProject.description}</p>

                                <div className="flex flex-wrap gap-2">
                                    {selectedProject.tags?.map(tag => (
                                        <span key={tag} className="inline-block bg-gray-100 text-gray-700 px-2 py-1 rounded text-sm">
                                            {tag}
                                        </span>
                                    ))}
                                </div>

                                <div className="border-t pt-4 space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-600">Status</span>
                                        <span className={`font-medium ${selectedProject.status === 'active' ? 'text-green-600' : 'text-gray-500'
                                            }`}>
                                            {selectedProject.status}
                                        </span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-600">Created</span>
                                        <span>{new Date(selectedProject.created_at).toLocaleDateString()}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-600">Last Updated</span>
                                        <span>{new Date(selectedProject.updated_at).toLocaleDateString()}</span>
                                    </div>
                                </div>

                                <div className="flex space-x-2 pt-4">
                                    <button
                                        onClick={() => navigate(`/projects/${selectedProject.id}/chat`)}
                                        className="flex-1 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                    >
                                        Open Chat
                                    </button>
                                    <button
                                        onClick={() => navigate(`/projects/${selectedProject.id}/files`)}
                                        className="flex-1 px-3 py-2 border border-gray-300 rounded hover:bg-gray-50"
                                    >
                                        View Files
                                    </button>
                                    {selectedProject.status === 'archived' ? (
                                        <button
                                            onClick={() => handleUnarchive(selectedProject.id)}
                                            className="flex-1 px-3 py-2 border border-gray-300 rounded hover:bg-gray-50"
                                        >
                                            Unarchive
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => handleArchive(selectedProject.id)}
                                            className="flex-1 px-3 py-2 border border-gray-300 rounded hover:bg-gray-50"
                                        >
                                            Archive
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Create Project Modal */}
                <CreateProjectModal
                    isOpen={showCreateModal}
                    onClose={() => setShowCreateModal(false)}
                    onSuccess={handleProjectCreated}
                />
            </div>
        </div>
    );
}
