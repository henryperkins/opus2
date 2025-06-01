/**
 * ProjectForm.jsx: Reusable form for creating and editing projects
 *
 * Handles validation, emoji/color picker, and tag management
 */
import React, { useState } from 'react';

const DEFAULT_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
  '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6B7280'
];

const DEFAULT_EMOJIS = [
  '=Á', '=€', '=¡', '<¯', '=%', 'P', '<¨', '=Ê', '<Æ',
  '=»', '=ñ', '<', '<ª', '<­', '<¨', '<¯', '=,', '¡', '<'
];

export default function ProjectForm({
  initialData = {},
  onSubmit,
  onCancel,
  loading = false,
  submitText = 'Create Project'
}) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'active',
    color: '#3B82F6',
    emoji: '=Á',
    tags: [],
    ...initialData
  });

  const [errors, setErrors] = useState({});
  const [tagInput, setTagInput] = useState('');

  const validateForm = () => {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    } else if (formData.title.length > 200) {
      newErrors.title = 'Title must be 200 characters or less';
    }

    if (formData.description && formData.description.length > 2000) {
      newErrors.description = 'Description must be 2000 characters or less';
    }

    if (!/^#[0-9A-Fa-f]{6}$/.test(formData.color)) {
      newErrors.color = 'Invalid color format';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleAddTag = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const tag = tagInput.trim().toLowerCase();
      if (tag && !formData.tags.includes(tag) && formData.tags.length < 20) {
        setFormData(prev => ({
          ...prev,
          tags: [...prev.tags, tag]
        }));
        setTagInput('');
      }
    }
  };

  const removeTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Title */}
      <div>
        <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
          Project Title *
        </label>
        <input
          id="title"
          type="text"
          value={formData.title}
          onChange={(e) => handleInputChange('title', e.target.value)}
          className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            errors.title ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder="Enter project title"
          maxLength={200}
        />
        {errors.title && <p className="mt-1 text-sm text-red-600">{errors.title}</p>}
      </div>

      {/* Description */}
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => handleInputChange('description', e.target.value)}
          rows={3}
          className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            errors.description ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder="Describe your project (optional)"
          maxLength={2000}
        />
        {errors.description && <p className="mt-1 text-sm text-red-600">{errors.description}</p>}
      </div>

      {/* Status */}
      <div>
        <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
          Status
        </label>
        <select
          id="status"
          value={formData.status}
          onChange={(e) => handleInputChange('status', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="active">Active</option>
          <option value="archived">Archived</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {/* Color and Emoji Row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Color Picker */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Project Color
          </label>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_COLORS.map(color => (
              <button
                key={color}
                type="button"
                onClick={() => handleInputChange('color', color)}
                className={`w-8 h-8 rounded-full border-2 ${
                  formData.color === color ? 'border-gray-800' : 'border-gray-300'
                }`}
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
          <input
            type="text"
            value={formData.color}
            onChange={(e) => handleInputChange('color', e.target.value)}
            className="mt-2 w-full px-3 py-1 text-sm border border-gray-300 rounded"
            placeholder="#3B82F6"
            pattern="^#[0-9A-Fa-f]{6}$"
          />
          {errors.color && <p className="mt-1 text-sm text-red-600">{errors.color}</p>}
        </div>

        {/* Emoji Picker */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Project Emoji
          </label>
          <div className="flex flex-wrap gap-1">
            {DEFAULT_EMOJIS.map(emoji => (
              <button
                key={emoji}
                type="button"
                onClick={() => handleInputChange('emoji', emoji)}
                className={`w-8 h-8 text-lg border rounded ${
                  formData.emoji === emoji ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
                title={emoji}
              >
                {emoji}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={formData.emoji}
            onChange={(e) => handleInputChange('emoji', e.target.value)}
            className="mt-2 w-full px-3 py-1 text-sm border border-gray-300 rounded"
            placeholder="=Á"
            maxLength={10}
          />
        </div>
      </div>

      {/* Tags */}
      <div>
        <label htmlFor="tags" className="block text-sm font-medium text-gray-700 mb-1">
          Tags
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {formData.tags.map(tag => (
            <span
              key={tag}
              className="inline-flex items-center px-2 py-1 text-sm bg-blue-100 text-blue-800 rounded-full"
            >
              #{tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="ml-1 text-blue-600 hover:text-blue-800"
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <input
          id="tags"
          type="text"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={handleAddTag}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Type a tag and press Enter or comma to add"
          maxLength={50}
        />
        <p className="mt-1 text-sm text-gray-500">
          {formData.tags.length}/20 tags " Press Enter or comma to add
        </p>
      </div>

      {/* Form Actions */}
      <div className="flex justify-end space-x-3 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          disabled={loading}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          disabled={loading}
        >
          {loading ? 'Saving...' : submitText}
        </button>
      </div>
    </form>
  );
}
