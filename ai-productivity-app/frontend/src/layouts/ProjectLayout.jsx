import { Outlet, useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { projectAPI } from '../api/projects';
import Breadcrumb from '../components/common/Breadcrumb';
import { Loader, AlertCircle, Settings, MoreHorizontal } from 'lucide-react';

export default function ProjectLayout() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (projectId) {
      loadProject();
    }
  }, [projectId]);

  const loadProject = async () => {
    try {
      setLoading(true);
      setError(null);
      const projectData = await projectAPI.get(projectId);
      setProject(projectData);
    } catch (err) {
      setError('Failed to load project');
      console.error('Failed to load project:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <Loader className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 text-center">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {error}
        </h2>
        <button
          onClick={loadProject}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Project Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4">
          <Breadcrumb showHome={false} />
          
          <div className="flex items-center justify-between mt-4">
            <div className="flex items-center space-x-3">
              {project?.color && (
                <div 
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: project.color }}
                  aria-label={`Project color: ${project.color}`}
                />
              )}
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {project?.name || 'Project'}
              </h1>
              {project?.status && (
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  project.status === 'active' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                }`}>
                  {project.status}
                </span>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                aria-label="Project settings"
              >
                <Settings className="w-5 h-5" />
              </button>
              <button
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                aria-label="More options"
              >
                <MoreHorizontal className="w-5 h-5" />
              </button>
            </div>
          </div>
          
          {project?.description && (
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              {project.description}
            </p>
          )}
        </div>
      </div>

      {/* Project Content */}
      <div className="px-6">
        <Outlet context={{ project }} />
      </div>
    </div>
  );
}