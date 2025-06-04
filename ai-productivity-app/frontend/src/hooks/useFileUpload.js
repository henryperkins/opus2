// Hook: useFileUpload
// -------------------
// Provides a reusable abstraction for uploading one or more code files to the
// backend while exposing progress, loading state, error message and a reset
// helper.  The hook *does not* decide where the uploaded files go – the caller
// must pass a projectId.

import { useState } from 'react';
import { codeAPI } from '../api/code';

export function useFileUpload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const uploadFiles = async (projectId, files) => {
    if (!projectId) throw new Error('projectId is required');
    if (!files || files.length === 0) return [];

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const res = await codeAPI.uploadFiles(projectId, files, (p) => {
        // p is 0-100, called by codeAPI via Axios onUploadProgress
        setProgress(Math.round(p));
      });
      return res;
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
      throw err;
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setUploading(false);
    setProgress(0);
    setError(null);
  };

  return { uploading, progress, error, uploadFiles, reset };
}
