/**
 * useFormHandling - Standardized form handling hook
 * 
 * Consolidates common form patterns to reduce duplication across components
 */
import { useState, useCallback, useMemo } from 'react';

/**
 * Standard form handling hook with validation, loading states, and error handling
 */
export const useFormHandling = (initialData = {}, validationRules = {}) => {
  const [formData, setFormData] = useState(initialData);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState({});

  // Update specific field
  const updateField = useCallback((field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  // Update multiple fields at once
  const updateFields = useCallback((updates) => {
    setFormData(prev => ({
      ...prev,
      ...updates
    }));
  }, []);

  // Mark field as touched
  const touchField = useCallback((field) => {
    setTouched(prev => ({
      ...prev,
      [field]: true
    }));
  }, []);

  // Validate single field
  const validateField = useCallback((field, value) => {
    const rules = validationRules[field];
    if (!rules) return null;

    for (const rule of rules) {
      const error = rule(value, formData);
      if (error) return error;
    }
    return null;
  }, [validationRules, formData]);

  // Validate all fields
  const validateForm = useCallback(() => {
    const newErrors = {};
    let isValid = true;

    Object.keys(validationRules).forEach(field => {
      const error = validateField(field, formData[field]);
      if (error) {
        newErrors[field] = error;
        isValid = false;
      }
    });

    setErrors(newErrors);
    return isValid;
  }, [formData, validateField, validationRules]);

  // Handle form submission
  const handleSubmit = useCallback(async (onSubmit, event) => {
    if (event) {
      event.preventDefault();
    }

    setLoading(true);
    
    // Mark all fields as touched
    const allTouched = Object.keys(validationRules).reduce((acc, field) => {
      acc[field] = true;
      return acc;
    }, {});
    setTouched(allTouched);

    try {
      const isValid = validateForm();
      if (!isValid) {
        setLoading(false);
        return false;
      }

      await onSubmit(formData);
      return true;
    } catch (error) {
      console.error('Form submission error:', error);
      
      // Handle server validation errors
      if (error.response?.data?.errors) {
        setErrors(error.response.data.errors);
      } else {
        setErrors({ 
          _general: error.message || 'An error occurred while submitting the form' 
        });
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, [formData, validateForm, validationRules]);

  // Reset form to initial state
  const resetForm = useCallback(() => {
    setFormData(initialData);
    setErrors({});
    setTouched({});
    setLoading(false);
  }, [initialData]);

  // Check if form has changes
  const hasChanges = useMemo(() => {
    return JSON.stringify(formData) !== JSON.stringify(initialData);
  }, [formData, initialData]);

  // Check if form is valid (no errors)
  const isValid = useMemo(() => {
    return Object.keys(errors).length === 0;
  }, [errors]);

  // Get field props (useful for controlled components)
  const getFieldProps = useCallback((field, type = 'text') => {
    const baseProps = {
      value: formData[field] || '',
      onChange: (e) => {
        const value = type === 'checkbox' ? e.target.checked : e.target.value;
        updateField(field, value);
      },
      onBlur: () => touchField(field),
    };

    if (type === 'checkbox') {
      return {
        ...baseProps,
        checked: Boolean(formData[field]),
      };
    }

    return baseProps;
  }, [formData, updateField, touchField]);

  // Get field error (only if touched)
  const getFieldError = useCallback((field) => {
    return touched[field] ? errors[field] : null;
  }, [touched, errors]);

  return {
    // State
    formData,
    errors,
    loading,
    touched,
    hasChanges,
    isValid,
    
    // Actions
    updateField,
    updateFields,
    touchField,
    validateField,
    validateForm,
    handleSubmit,
    resetForm,
    
    // Helpers
    getFieldProps,
    getFieldError,
  };
};

/**
 * Common validation rules
 */
export const validationRules = {
  required: (message = 'This field is required') => (value) => {
    if (!value || (typeof value === 'string' && !value.trim())) {
      return message;
    }
    return null;
  },
  
  minLength: (min, message) => (value) => {
    if (value && value.length < min) {
      return message || `Must be at least ${min} characters`;
    }
    return null;
  },
  
  maxLength: (max, message) => (value) => {
    if (value && value.length > max) {
      return message || `Must be no more than ${max} characters`;
    }
    return null;
  },
  
  email: (message = 'Please enter a valid email address') => (value) => {
    if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      return message;
    }
    return null;
  },
  
  url: (message = 'Please enter a valid URL') => (value) => {
    if (value) {
      try {
        new URL(value);
      } catch {
        return message;
      }
    }
    return null;
  },
  
  pattern: (regex, message) => (value) => {
    if (value && !regex.test(value)) {
      return message;
    }
    return null;
  },
  
  custom: (validator, message) => (value, formData) => {
    if (!validator(value, formData)) {
      return message;
    }
    return null;
  },
};

/**
 * Pre-configured form handlers for common use cases
 */
export const useProjectForm = (initialData = {}) => {
  const validation = {
    title: [
      validationRules.required('Title is required'),
      validationRules.maxLength(200, 'Title must be 200 characters or less'),
    ],
    description: [
      validationRules.maxLength(2000, 'Description must be 2000 characters or less'),
    ],
  };

  return useFormHandling({
    title: '',
    description: '',
    status: 'active',
    color: '#3B82F6',
    emoji: '🚀',
    tags: [],
    ...initialData
  }, validation);
};

export const useAuthForm = (type = 'login') => {
  const baseValidation = {
    email: [
      validationRules.required('Email is required'),
      validationRules.email(),
    ],
    password: [
      validationRules.required('Password is required'),
      validationRules.minLength(8, 'Password must be at least 8 characters'),
    ],
  };

  if (type === 'register') {
    baseValidation.username = [
      validationRules.required('Username is required'),
      validationRules.minLength(3, 'Username must be at least 3 characters'),
    ];
    baseValidation.confirmPassword = [
      validationRules.required('Please confirm your password'),
      validationRules.custom(
        (value, formData) => value === formData.password,
        'Passwords do not match'
      ),
    ];
  }

  const initialData = type === 'register' 
    ? { username: '', email: '', password: '', confirmPassword: '' }
    : { email: '', password: '' };

  return useFormHandling(initialData, baseValidation);
};

export const useSettingsForm = (initialData = {}) => {
  const validation = {
    username: [
      validationRules.required('Username is required'),
      validationRules.minLength(3, 'Username must be at least 3 characters'),
    ],
    email: [
      validationRules.required('Email is required'),
      validationRules.email(),
    ],
  };

  return useFormHandling({
    username: '',
    email: '',
    ...initialData
  }, validation);
};

export default {
  useFormHandling,
  validationRules,
  useProjectForm,
  useAuthForm,
  useSettingsForm,
};
