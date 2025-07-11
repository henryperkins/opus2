/* ProjectFilesPage.jsx – Browse & upload source files for a project */

import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { useFileUpload } from "../hooks/useFileUpload";
import { toast } from "../components/common/Toast";

// Custom hook for project files
function useProjectFiles(projectId) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      // Import codeAPI dynamically to avoid ESLint restriction
      const { codeAPI } = await import("../api/code");
      const data = await codeAPI.getProjectFiles(projectId);
      setFiles(data.files || data || []);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { files, loading, error, refresh };
}

export default function ProjectFilesPage() {
  const { projectId } = useParams();
  const { files, loading, error, refresh } = useProjectFiles(projectId);
  const { uploadFiles, uploading } = useFileUpload();

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleUpload = async (e) => {
    const selected = Array.from(e.target.files);
    if (!selected.length) return;
    try {
      await uploadFiles(projectId, selected);
      await refresh();
      toast.success("Files uploaded successfully");
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message);
    } finally {
      e.target.value = "";
    }
  };

  return (
    <main className="max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Project Files</h1>

        <label className="inline-flex items-center cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-800">
          <input
            type="file"
            multiple
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
          {uploading ? "Uploading…" : "Upload Files"}
        </label>
      </div>

      {loading && <p className="text-gray-500">Loading files…</p>}
      {error && <p className="text-red-600">{error}</p>}

      {!loading && files.length === 0 && (
        <p className="text-gray-400">No files indexed for this project.</p>
      )}

      {!loading && files.length > 0 && (
        <ul className="divide-y divide-gray-200 bg-white shadow-sm rounded-md">
          {files.map((f, index) => (
            <li
              key={f.id || `${f.path || f.filename}-${index}`}
              className="px-4 py-3 text-sm flex justify-between"
            >
              <span className="font-medium text-gray-800 truncate mr-4">
                {f.path || f.filename}
              </span>
              <span className="text-gray-500">
                {(f.language || "").toUpperCase()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
