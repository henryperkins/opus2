import { Outlet, useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { projectAPI } from '../api/projects';
import { Loader, AlertCircle } from 'lucide-react';

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

  // REMOVED: Entire header section with duplicate breadcrumbs and title
  // Navigation is now handled by UnifiedNavBar which includes project info and breadcrumbs
  return <Outlet context={{ project }} />;
}