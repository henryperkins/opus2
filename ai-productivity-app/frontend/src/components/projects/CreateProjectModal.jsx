/**
 * CreateProjectModal.jsx: Modal wrapper for project creation
 * 
 * Provides a modal interface for creating new projects with form validation
 * and success/error handling.
 */
import React, { useState } from 'react';
import Modal from '../common/Modal';
import ProjectForm from './ProjectForm';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectAPI } from '../../api/projects';

export default function CreateProjectModal({ isOpen, onClose, onSuccess }) {
  const queryClient = useQueryClient();
  const [localError, setLocalError] = useState(null);
  
  const createProjectMutation = useMutation({
    mutationFn: (formData) => projectAPI.create(formData),
    onSuccess: (project) => {
      queryClient.invalidateQueries(['projects']);
      if (onSuccess) {
        onSuccess(project);
      }
      onClose();
    },
    onError: (error) => {
      setLocalError(error.message || 'Failed to create project');
    }
  });

  const handleSubmit = async (formData) => {
    setLocalError(null);
    createProjectMutation.mutate(formData);
  };

  const handleClose = () => {
    setLocalError(null);
    onClose();
  };

  const displayError = localError || createProjectMutation.error?.message;

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
          loading={createProjectMutation.isLoading}
          submitText="Create Project"
        />
      </div>
    </Modal>
  );
}