// frontend/src/hooks/useProject.js
import { useState, useEffect } from "react";
import { projectAPI } from "../api/projects";

export function useProject(projectId) {
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
      setError("Failed to load project");
      console.error("Failed to load project:", err);
    } finally {
      setLoading(false);
    }
  };

  return { project, loading, error, loadProject };
}
