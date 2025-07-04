/**
 * CreateProjectModal.jsx: Modal wrapper for project creation
 * 
 * Provides a modal interface for creating new projects with form validation
 * and success/error handling.
 */
import React, { useState } from 'react';
import UnifiedModal from "../../components/common/UnifiedModal";
import ProjectForm from './ProjectForm';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectAPI } from '../../api/projects';

export default function CreateProjectModal({ isOpen, onClose, onSuccess }) {
  const [localError, setLocalError] = useState(null);
  const queryClient = useQueryClient();
  
  const mutation = useMutation({
    mutationFn: projectAPI.create,
    onSuccess: (data) => {
      // Invalidate and refetch projects list
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      
      // Clear any local errors
      setLocalError(null);
      
      // Call success callback if provided
      if (onSuccess) {
        onSuccess(data);
      }
      
      // Close modal
      onClose();
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.detail || 
                          error.message || 
                          'Failed to create project. Please try again.';
      setLocalError(errorMessage);
    }
  });
  
  const handleSubmit = async (formData) => {
    setLocalError(null);
    mutation.mutate(formData);
  };

  const handleClose = () => {
    setLocalError(null);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create New Project" closeOnOverlayClick={false}>
      <div className="mt-4">
        {localError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{localError}</p>
          </div>
        )}
        
        <ProjectForm
          onSubmit={handleSubmit}
          onCancel={handleClose}
          loading={mutation.isPending}
          submitText="Create Project"
        />
      </div>
    </Modal>
  );
}