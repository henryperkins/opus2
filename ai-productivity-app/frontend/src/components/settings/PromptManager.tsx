// components/settings/PromptManager.tsx
import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Copy, Save, X, FileText, Share2, Lock } from 'lucide-react';
import { promptAPI } from '../../api/prompts';
import { toast } from '../common/Toast';

interface Variable {
  name: string;
  description: string;
  defaultValue?: string;
  required: boolean;
}

interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  systemPrompt: string;
  userPromptTemplate: string;
  variables: Variable[];
  modelPreferences?: {
    provider?: string;
    model?: string;
    temperature?: number;
    maxTokens?: number;
  };
  isPublic: boolean;
  isDefault: boolean;
  usageCount: number;
  createdAt: string;
  updatedAt: string;
}

const categories = [
  'Code Generation',
  'Code Review',
  'Documentation',
  'Testing',
  'Debugging',
  'Refactoring',
  'Architecture',
  'Custom'
];

const defaultTemplates: Partial<PromptTemplate>[] = [
  {
    name: 'Code Explainer',
    description: 'Explains code functionality in detail',
    category: 'Documentation',
    systemPrompt: 'You are an expert programmer who excels at explaining code clearly and concisely.',
    userPromptTemplate: 'Please explain the following {{language}} code:\n\n```{{language}}\n{{code}}\n```\n\nFocus on:\n1. Overall purpose\n2. Key logic flow\n3. Important details\n{{additionalContext}}',
    variables: [
      { name: 'language', description: 'Programming language', required: true },
      { name: 'code', description: 'Code to explain', required: true },
      { name: 'additionalContext', description: 'Additional context or specific questions', required: false }
    ],
    isDefault: true
  },
  {
    name: 'Test Generator',
    description: 'Generates comprehensive unit tests',
    category: 'Testing',
    systemPrompt: 'You are a testing expert who writes comprehensive, well-structured unit tests.',
    userPromptTemplate: 'Generate {{testFramework}} unit tests for the following {{language}} code:\n\n```{{language}}\n{{code}}\n```\n\nRequirements:\n- Cover all functions/methods\n- Include edge cases\n- Add helpful test descriptions\n{{additionalRequirements}}',
    variables: [
      { name: 'language', description: 'Programming language', required: true },
      { name: 'testFramework', description: 'Test framework (e.g., Jest, pytest)', required: true },
      { name: 'code', description: 'Code to test', required: true },
      { name: 'additionalRequirements', description: 'Additional test requirements', required: false }
    ],
    modelPreferences: {
      temperature: 0.3,
      maxTokens: 2048
    },
    isDefault: true
  }
];

export default function PromptManager() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [testingPrompt, setTestingPrompt] = useState<string | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await promptAPI.getTemplates();
      setTemplates(response.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
      // Use default templates as fallback
      setTemplates(defaultTemplates.map((t, i) => ({
        ...t,
        id: `default-${i}`,
        isPublic: false,
        usageCount: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      } as PromptTemplate)));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveTemplate = async (template: Partial<PromptTemplate>) => {
    try {
      if (editingTemplate) {
        await promptAPI.updateTemplate(editingTemplate.id, template);
        toast.success('Template updated successfully');
      } else {
        await promptAPI.createTemplate(template);
        toast.success('Template created successfully');
      }
      await loadTemplates();
      setEditingTemplate(null);
      setIsCreating(false);
    } catch (error) {
      toast.error('Failed to save template');
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      await promptAPI.deleteTemplate(id);
      toast.success('Template deleted successfully');
      await loadTemplates();
    } catch (error) {
      toast.error('Failed to delete template');
    }
  };

  const handleDuplicateTemplate = async (template: PromptTemplate) => {
    const newTemplate = {
      ...template,
      name: `${template.name} (Copy)`,
      isDefault: false,
      isPublic: false
    };
    delete (newTemplate as any).id;

    try {
      await promptAPI.createTemplate(newTemplate);
      toast.success('Template duplicated successfully');
      await loadTemplates();
    } catch (error) {
      toast.error('Failed to duplicate template');
    }
  };

  const handleTestPrompt = (template: PromptTemplate) => {
    setTestingPrompt(template.id);
    // Initialize variable values with defaults
    const defaults: Record<string, string> = {};
    template.variables.forEach(v => {
      defaults[v.name] = v.defaultValue || '';
    });
    setVariableValues(defaults);
  };

  const executeTestPrompt = async () => {
    const template = templates.find(t => t.id === testingPrompt);
    if (!template) return;

    // Validate required variables
    const missingVars = template.variables
      .filter(v => v.required && !variableValues[v.name])
      .map(v => v.name);

    if (missingVars.length > 0) {
      toast.error(`Missing required variables: ${missingVars.join(', ')}`);
      return;
    }

    // Build prompt
    let userPrompt = template.userPromptTemplate;
    Object.entries(variableValues).forEach(([name, value]) => {
      userPrompt = userPrompt.replace(new RegExp(`{{${name}}}`, 'g'), value);
    });

    // Here you would send to the chat
    console.log('System prompt:', template.systemPrompt);
    console.log('User prompt:', userPrompt);
    console.log('Model preferences:', template.modelPreferences);

    toast.success('Prompt sent to chat');
    setTestingPrompt(null);
  };

  const filteredTemplates = templates.filter(template => {
    const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
    const matchesSearch = !searchQuery ||
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/4"></div>
        <div className="h-64 bg-gray-200 rounded"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Prompt Templates</h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage and organize your prompt templates for consistent AI interactions
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>New Template</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center space-x-4">
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-3 py-2 border rounded-lg"
          />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 border rounded-lg"
          >
            <option value="all">All Categories</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map(template => (
          <div key={template.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
            <div className="p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900 flex items-center">
                    {template.name}
                    {template.isDefault && (
                      <Lock className="w-3 h-3 ml-2 text-gray-400" title="Default template" />
                    )}
                    {template.isPublic && (
                      <Share2 className="w-3 h-3 ml-2 text-blue-500" title="Public template" />
                    )}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                </div>
              </div>

              <div className="flex items-center justify-between mt-3">
                <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                  {template.category}
                </span>
                <span className="text-xs text-gray-500">
                  Used {template.usageCount} times
                </span>
              </div>

              {template.variables.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <div className="text-xs text-gray-600">
                    Variables: {template.variables.map(v => v.name).join(', ')}
                  </div>
                </div>
              )}

              <div className="flex items-center space-x-2 mt-4">
                <button
                  onClick={() => handleTestPrompt(template)}
                  className="flex-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm"
                >
                  Test
                </button>
                {!template.isDefault && (
                  <>
                    <button
                      onClick={() => setEditingTemplate(template)}
                      className="p-1.5 text-gray-600 hover:text-gray-800"
                      title="Edit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteTemplate(template.id)}
                      className="p-1.5 text-red-600 hover:text-red-800"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </>
                )}
                <button
                  onClick={() => handleDuplicateTemplate(template)}
                  className="p-1.5 text-gray-600 hover:text-gray-800"
                  title="Duplicate"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Template Editor Modal */}
      {(editingTemplate || isCreating) && (
        <TemplateEditor
          template={editingTemplate || {
            name: '',
            description: '',
            category: 'Custom',
            systemPrompt: '',
            userPromptTemplate: '',
            variables: [],
            isPublic: false,
            isDefault: false
          } as any}
          onSave={handleSaveTemplate}
          onCancel={() => {
            setEditingTemplate(null);
            setIsCreating(false);
          }}
        />
      )}

      {/* Test Prompt Modal */}
      {testingPrompt && (
        <TestPromptModal
          template={templates.find(t => t.id === testingPrompt)!}
          variableValues={variableValues}
          onVariableChange={(name, value) => setVariableValues({ ...variableValues, [name]: value })}
          onExecute={executeTestPrompt}
          onCancel={() => setTestingPrompt(null)}
        />
      )}
    </div>
  );
}

// Template Editor Component
function TemplateEditor({
  template,
  onSave,
  onCancel
}: {
  template: Partial<PromptTemplate>;
  onSave: (template: Partial<PromptTemplate>) => void;
  onCancel: () => void;
}) {
  const [formData, setFormData] = useState(template);
  const [newVariable, setNewVariable] = useState({ name: '', description: '', required: false });

  const handleAddVariable = () => {
    if (!newVariable.name) return;

    setFormData({
      ...formData,
      variables: [...(formData.variables || []), { ...newVariable, defaultValue: '' }]
    });
    setNewVariable({ name: '', description: '', required: false });
  };

  const handleRemoveVariable = (index: number) => {
    const vars = [...(formData.variables || [])];
    vars.splice(index, 1);
    setFormData({ ...formData, variables: vars });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h3 className="text-lg font-medium">
            {template.id ? 'Edit Template' : 'Create New Template'}
          </h3>
        </div>

        <div className="p-6 space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={formData.category || 'Custom'}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <input
              type="text"
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              System Prompt
            </label>
            <textarea
              value={formData.systemPrompt || ''}
              onChange={(e) => setFormData({ ...formData, systemPrompt: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg h-24"
              placeholder="Define the AI's role and behavior..."
            />
          </div>

          {/* User Prompt Template */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              User Prompt Template
            </label>
            <textarea
              value={formData.userPromptTemplate || ''}
              onChange={(e) => setFormData({ ...formData, userPromptTemplate: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg h-32 font-mono text-sm"
              placeholder="Use {{variableName}} for variables..."
            />
          </div>

          {/* Variables */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Variables</h4>

            {(formData.variables || []).map((variable, index) => (
              <div key={index} className="flex items-center space-x-2 mb-2">
                <input
                  type="text"
                  value={variable.name}
                  readOnly
                  className="flex-1 px-2 py-1 border rounded text-sm bg-gray-50"
                />
                <input
                  type="text"
                  value={variable.description}
                  readOnly
                  className="flex-2 px-2 py-1 border rounded text-sm bg-gray-50"
                />
                <button
                  onClick={() => handleRemoveVariable(index)}
                  className="p-1 text-red-600 hover:text-red-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}

            <div className="flex items-center space-x-2 mt-2">
              <input
                type="text"
                placeholder="Variable name"
                value={newVariable.name}
                onChange={(e) => setNewVariable({ ...newVariable, name: e.target.value })}
                className="flex-1 px-2 py-1 border rounded text-sm"
              />
              <input
                type="text"
                placeholder="Description"
                value={newVariable.description}
                onChange={(e) => setNewVariable({ ...newVariable, description: e.target.value })}
                className="flex-2 px-2 py-1 border rounded text-sm"
              />
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={newVariable.required}
                  onChange={(e) => setNewVariable({ ...newVariable, required: e.target.checked })}
                  className="mr-1"
                />
                <span className="text-sm">Required</span>
              </label>
              <button
                onClick={handleAddVariable}
                className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                Add
              </button>
            </div>
          </div>

          {/* Privacy */}
          <div className="flex items-center space-x-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.isPublic || false}
                onChange={(e) => setFormData({ ...formData, isPublic: e.target.checked })}
                className="mr-2"
              />
              <span className="text-sm">Make this template public</span>
            </label>
          </div>
        </div>

        <div className="p-6 border-t flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(formData)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Save Template
          </button>
        </div>
      </div>
    </div>
  );
}

// Test Prompt Modal
function TestPromptModal({
  template,
  variableValues,
  onVariableChange,
  onExecute,
  onCancel
}: {
  template: PromptTemplate;
  variableValues: Record<string, string>;
  onVariableChange: (name: string, value: string) => void;
  onExecute: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h3 className="text-lg font-medium">Test: {template.name}</h3>
        </div>

        <div className="p-6 space-y-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">System Prompt</h4>
            <p className="text-sm text-gray-600">{template.systemPrompt}</p>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Variables</h4>
            {template.variables.map(variable => (
              <div key={variable.name} className="mb-3">
                <label className="block text-sm text-gray-600 mb-1">
                  {variable.description || variable.name}
                  {variable.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                <textarea
                  value={variableValues[variable.name] || ''}
                  onChange={(e) => onVariableChange(variable.name, e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  rows={3}
                  placeholder={`Enter ${variable.name}...`}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="p-6 border-t flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            Cancel
          </button>
          <button
            onClick={onExecute}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Send to Chat
          </button>
        </div>
      </div>
    </div>
  );
}
