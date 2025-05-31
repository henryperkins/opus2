/**
 * CreateProjectModal.jsx: Modal wrapper for project creation
 * 
 * Provides a modal interface for creating new projects with form validation
 * and success/error handling.
 */
import React, { useState } from 'react';
import Modal from '../common/Modal';
import ProjectForm from './ProjectForm';
import useProjectStore from '../../stores/projectStore';

export default function CreateProjectModal({ isOpen, onClose, onSuccess }) {
  const { createProject, loading, error, clearError } = useProjectStore();
  const [localError, setLocalError] = useState(null);

  const handleSubmit = async (formData) => {
    try {
      setLocalError(null);
      clearError();
      
      const project = await createProject(formData);
      
      if (onSuccess) {
        onSuccess(project);
      }
      
      onClose();
    } catch (err) {
      setLocalError(err.message || 'Failed to create project');
    }
  };

  const handleClose = () => {
    setLocalError(null);
    clearError();
    onClose();
  };

  const displayError = localError || error;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create New Project">
      <div className="mt-4">
        {displayError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{displayError}</p>
          </div>
        )}
        
        <ProjectForm
          onSubmit={handleSubmit}
          onCancel={handleClose}
          loading={loading}
          submitText="Create Project"
        />
      </div>
    </Modal>
  );
}