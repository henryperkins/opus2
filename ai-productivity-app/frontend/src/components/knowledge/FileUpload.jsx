// Knowledge document upload interface with drag-and-drop support and progress tracking
import React, { useCallback, useState, useRef } from 'react';
import { Upload, X, FileText, File, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import PropTypes from 'prop-types';

const ALLOWED_FILE_TYPES = {
  'text/plain': { label: 'Text Files', ext: '.txt' },
  'text/markdown': { label: 'Markdown', ext: '.md' },
  'application/pdf': { label: 'PDF Documents', ext: '.pdf' },
  'text/html': { label: 'HTML Files', ext: '.html' },
  'application/json': { label: 'JSON Files', ext: '.json' },
  'text/yaml': { label: 'YAML Files', ext: '.yml,.yaml' },
  'text/csv': { label: 'CSV Files', ext: '.csv' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { label: 'Word Documents', ext: '.docx' },
  'application/msword': { label: 'Word Documents', ext: '.doc' }
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_FILES = 10;

export default function FileUpload({ 
  projectId, 
  onSuccess, 
  onError, 
  category = "general",
  disabled = false 
}) {
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState([]);
  const fileInputRef = useRef(null);

  const validateFile = useCallback((file) => {
    const errors = [];
    
    // Check file type
    if (!ALLOWED_FILE_TYPES[file.type] && file.type !== '') {
      errors.push(`Unsupported file type: ${file.type}`);
    }
    
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      errors.push(`File too large: ${(file.size / 1024 / 1024).toFixed(2)}MB (max: 10MB)`);
    }
    
    return errors;
  }, []);

  const handleFiles = useCallback((newFiles) => {
    const validFiles = [];
    const fileErrors = [];

    Array.from(newFiles).forEach(file => {
      const errors = validateFile(file);
      if (errors.length === 0) {
        validFiles.push({
          file,
          id: Math.random().toString(36).substr(2, 9),
          name: file.name,
          size: file.size,
          type: file.type || 'text/plain',
          status: 'pending'
        });
      } else {
        fileErrors.push({ name: file.name, errors });
      }
    });

    if (fileErrors.length > 0) {
      onError?.(fileErrors);
    }

    setFiles(prevFiles => {
      const combined = [...prevFiles, ...validFiles];
      return combined.slice(0, MAX_FILES); // Limit total files
    });
  }, [validateFile, onError]);

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      handleFiles(droppedFiles);
    }
  }, [handleFiles]);

  const handleFileSelect = useCallback((e) => {
    const selectedFiles = e.target.files;
    if (selectedFiles.length > 0) {
      handleFiles(selectedFiles);
    }
  }, [handleFiles]);

  const removeFile = useCallback((fileId) => {
    setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
  }, []);

  const uploadFiles = useCallback(async () => {
    if (files.length === 0 || uploading) return;

    setUploading(true);
    setUploadResults([]);

    try {
      const formData = new FormData();
      files.forEach(fileItem => {
        formData.append('files', fileItem.file);
      });
      formData.append('category', category);

      const response = await fetch(`/api/knowledge/projects/${projectId}/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.success) {
        setUploadResults(result.results || []);
        
        // Update file statuses based on results
        setFiles(prevFiles => 
          prevFiles.map(fileItem => {
            const uploadResult = result.results?.find(r => 
              r.file === fileItem.name || r.title === fileItem.name
            );
            
            return {
              ...fileItem,
              status: uploadResult?.status || 'success'
            };
          })
        );

        onSuccess?.(result);
        
        // Clear files after successful upload
        setTimeout(() => {
          setFiles([]);
          setUploadResults([]);
        }, 3000);
      } else {
        throw new Error(result.message || 'Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      onError?.(error.message);
      
      // Mark all files as failed
      setFiles(prevFiles => 
        prevFiles.map(fileItem => ({
          ...fileItem,
          status: 'error'
        }))
      );
    } finally {
      setUploading(false);
    }
  }, [files, uploading, projectId, category, onSuccess, onError]);

  const getFileIcon = (type) => {
    if (type.includes('text') || type.includes('markdown')) {
      return FileText;
    }
    return File;
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
      case 'rejected':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'uploading':
        return <Loader className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return null;
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        className={`relative border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : disabled
            ? 'border-gray-200 bg-gray-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={Object.keys(ALLOWED_FILE_TYPES).join(',')}
          onChange={handleFileSelect}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={disabled || uploading}
        />

        <div className="space-y-2">
          <Upload className={`w-8 h-8 mx-auto ${disabled ? 'text-gray-400' : 'text-gray-500'}`} />
          <div>
            <p className={`text-sm font-medium ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
              {dragActive ? 'Drop files here' : 'Drag & drop knowledge documents'}
            </p>
            <p className={`text-xs ${disabled ? 'text-gray-300' : 'text-gray-500'}`}>
              or click to browse ({MAX_FILES} files max, 10MB each)
            </p>
          </div>
        </div>

        {/* Supported formats */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 mb-2">Supported formats:</p>
          <div className="flex flex-wrap gap-1 justify-center">
            {Object.values(ALLOWED_FILE_TYPES).map((format, idx) => (
              <span key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded">
                {format.ext}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-700">
              Files to upload ({files.length})
            </h4>
            <button
              onClick={uploadFiles}
              disabled={uploading || disabled}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {uploading && <Loader className="w-4 h-4 animate-spin" />}
              <span>{uploading ? 'Uploading...' : 'Upload Files'}</span>
            </button>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            {files.map((fileItem) => {
              const FileIcon = getFileIcon(fileItem.type);
              return (
                <div
                  key={fileItem.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <FileIcon className="w-5 h-5 text-gray-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {fileItem.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(fileItem.size)} • {ALLOWED_FILE_TYPES[fileItem.type]?.label || 'Unknown'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    {getStatusIcon(fileItem.status)}
                    {!uploading && fileItem.status === 'pending' && (
                      <button
                        onClick={() => removeFile(fileItem.id)}
                        className="p-1 text-gray-400 hover:text-gray-600 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Upload Results */}
      {uploadResults.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Upload Results</h4>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {uploadResults.map((result, idx) => (
              <div
                key={idx}
                className={`p-2 rounded text-xs ${
                  result.status === 'success'
                    ? 'bg-green-50 text-green-700'
                    : result.status === 'duplicate'
                    ? 'bg-yellow-50 text-yellow-700'
                    : 'bg-red-50 text-red-700'
                }`}
              >
                <div className="font-medium">{result.file}</div>
                {result.reason && (
                  <div className="text-xs opacity-75">{result.reason}</div>
                )}
                {result.existing_title && (
                  <div className="text-xs opacity-75">Existing: {result.existing_title}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

FileUpload.propTypes = {
  projectId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  onSuccess: PropTypes.func,
  onError: PropTypes.func,
  category: PropTypes.string,
  disabled: PropTypes.bool,
};