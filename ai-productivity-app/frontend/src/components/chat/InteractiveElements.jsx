/* eslint-disable */
// components/chat/InteractiveElements.jsx
import { useState } from 'react';
import {
  Play, Code, ChevronRight, Check, X, AlertCircle, Loader, Copy, Edit2, RotateCcw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Enhanced Executable Code Block
const ExecutableCode = ({
  element,
  onComplete
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [editedCode, setEditedCode] = useState(element.data.code);
  const [isEditing, setIsEditing] = useState(false);
  const [executionTime, setExecutionTime] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleRun = async () => {
    setIsRunning(true);
    setOutput(null);
    setError(null);
    const startTime = Date.now();

    try {
      const result = await element.onInteraction('run', {
        code: editedCode,
        language: element.data.language
      });

      setOutput(result.output);
      setExecutionTime(Date.now() - startTime);
      onComplete?.(result);
    } catch (err) {
      setError(err.message || 'Execution failed');
    } finally {
      setIsRunning(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(editedCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const handleEdit = () => {
    setIsEditing(!isEditing);
  };

  const handleSave = () => {
    setIsEditing(false);
    // Optionally notify parent of code changes
  };

  const handleReset = () => {
    setEditedCode(element.data.code);
    setIsEditing(false);
    setOutput(null);
    setError(null);
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="bg-gray-100 dark:bg-gray-800 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Code className="w-4 h-4 text-gray-600" />
          <span className="text-sm font-medium">{element.data.language}</span>
          {executionTime && (
            <span className="text-xs text-gray-500">({executionTime}ms)</span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="p-1 text-gray-600 hover:text-gray-800 transition-colors"
            title="Copy code"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-600" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={handleEdit}
            className={`p-1 transition-colors ${isEditing ? 'text-blue-600' : 'text-gray-600 hover:text-gray-800'}`}
            title="Edit code"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          {editedCode !== element.data.code && (
            <button
              onClick={handleReset}
              className="p-1 text-gray-600 hover:text-gray-800 transition-colors"
              title="Reset to original"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 text-sm"
          >
            {isRunning ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            <span>{isRunning ? 'Running...' : 'Run'}</span>
          </button>
        </div>
      </div>

      {isEditing ? (
        <div className="relative">
          <textarea
            value={editedCode}
            onChange={(e) => setEditedCode(e.target.value)}
            className="w-full p-4 bg-gray-50 dark:bg-gray-900 font-mono text-sm resize-none border-none focus:outline-none"
            rows={Math.max(3, editedCode.split('\n').length)}
            style={{ minHeight: '120px' }}
          />
          <div className="absolute bottom-2 right-2 flex space-x-2">
            <button
              onClick={() => setIsEditing(false)}
              className="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <pre className="p-4 bg-gray-50 dark:bg-gray-900 overflow-x-auto">
          <code className="text-sm">{editedCode}</code>
        </pre>
      )}

      <AnimatePresence>
        {(output || error) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t"
          >
            <div className={`p-4 ${error ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'}`}>
              <div className="flex items-start space-x-2">
                {error ? (
                  <AlertCircle className="w-4 h-4 text-red-600 mt-0.5" />
                ) : (
                  <Check className="w-4 h-4 text-green-600 mt-0.5" />
                )}
                <pre className="text-sm flex-1 whitespace-pre-wrap">
                  {error || output}
                </pre>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Interactive Query Builder
const QueryBuilder = ({
  element,
  onComplete
}) => {
  const [query, setQuery] = useState(element.data.initialQuery || '');
  const [filters, setFilters] = useState(element.data.filters || {});
  const [isExecuting, setIsExecuting] = useState(false);
  const [results, setResults] = useState(null);

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      const result = await element.onInteraction('execute', { query, filters });
      setResults(result.data);
      onComplete?.(result);
    } catch (error) {
      console.error('Query execution failed:', error);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="border rounded-lg p-4 space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Query
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full px-3 py-2 border rounded-lg text-sm font-mono"
          rows={3}
          placeholder="Enter your query..."
        />
      </div>

      {Object.keys(element.data.availableFilters || {}).map(filterKey => (
        <div key={filterKey}>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {element.data.availableFilters[filterKey].label}
          </label>
          <input
            type={element.data.availableFilters[filterKey].type || 'text'}
            value={filters[filterKey] || ''}
            onChange={(e) => setFilters({ ...filters, [filterKey]: e.target.value })}
            className="w-full px-3 py-2 border rounded-lg text-sm"
            placeholder={element.data.availableFilters[filterKey].placeholder}
          />
        </div>
      ))}

      <button
        onClick={handleExecute}
        disabled={isExecuting || !query}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {isExecuting ? 'Executing...' : 'Execute Query'}
      </button>

      {results && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h4 className="text-sm font-medium mb-2">Results ({results.length})</h4>
          <pre className="text-xs overflow-x-auto">
            {JSON.stringify(results, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

// Decision Tree
const DecisionTree = ({
  element,
  onComplete
}) => {
  const [currentNode, setCurrentNode] = useState(element.data.root);
  const [path, setPath] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleChoice = async (choice) => {
    setIsProcessing(true);
    const newPath = [...path, choice.label];
    setPath(newPath);

    try {
      const result = await element.onInteraction('choose', {
        nodeId: currentNode.id,
        choice: choice.value,
        path: newPath
      });

      if (result.nextNode) {
        setCurrentNode(result.nextNode);
      } else {
        onComplete?.(result);
      }
    } catch (error) {
      console.error('Decision processing failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBack = () => {
    if (path.length > 0) {
      const newPath = path.slice(0, -1);
      setPath(newPath);

      // Navigate back by reconstructing the path
      if (newPath.length === 0) {
        setCurrentNode(element.data.root);
      } else {
        // Traverse the tree following the remaining path
        let node = element.data.root;
        for (const stepLabel of newPath) {
          const choice = node.choices.find(c => c.label === stepLabel);
          if (choice && choice.nextNode) {
            node = choice.nextNode;
          } else {
            // Fallback to root if path is invalid
            console.warn('Invalid path detected, resetting to root');
            node = element.data.root;
            setPath([]);
            break;
          }
        }
        setCurrentNode(node);
      }
    }
  };

  return (
    <div className="border rounded-lg p-4">
      {path.length > 0 && (
        <div className="mb-4">
          <button
            onClick={handleBack}
            className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
          >
            <ChevronRight className="w-4 h-4 rotate-180" />
            Back
          </button>
          <div className="mt-2 text-xs text-gray-600">
            Path: {path.join(' → ')}
          </div>
        </div>
      )}

      <div className="space-y-3">
        <h4 className="font-medium text-gray-900">{currentNode.question}</h4>

        {currentNode.description && (
          <p className="text-sm text-gray-600">{currentNode.description}</p>
        )}

        <div className="space-y-2">
          {currentNode.choices.map((choice, idx) => (
            <button
              key={idx}
              onClick={() => handleChoice(choice)}
              disabled={isProcessing}
              className="w-full text-left p-3 border rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{choice.label}</div>
                  {choice.description && (
                    <div className="text-xs text-gray-600 mt-1">{choice.description}</div>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

// Dynamic Form
const DynamicForm = ({
  element,
  onComplete
}) => {
  const [formData, setFormData] = useState(element.data.initialValues || {});
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrors({});

    try {
      const result = await element.onInteraction('submit', formData);
      onComplete?.(result);
    } catch (error) {
      if (error.validationErrors) {
        setErrors(error.validationErrors);
      } else {
        console.error('Form submission failed:', error);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setFormData({ ...formData, [fieldName]: value });
    // Clear error for this field
    if (errors[fieldName]) {
      setErrors({ ...errors, [fieldName]: '' });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border rounded-lg p-4 space-y-4">
      <h4 className="font-medium text-gray-900">{element.data.title}</h4>

      {element.data.fields.map((field) => (
        <div key={field.name}>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>

          {field.type === 'select' ? (
            <select
              value={formData[field.name] || ''}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              required={field.required}
            >
              <option value="">Select...</option>
              {field.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          ) : field.type === 'textarea' ? (
            <textarea
              value={formData[field.name] || ''}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              rows={field.rows || 3}
              required={field.required}
              placeholder={field.placeholder}
            />
          ) : (
            <input
              type={field.type || 'text'}
              value={formData[field.name] || ''}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              required={field.required}
              placeholder={field.placeholder}
            />
          )}

          {errors[field.name] && (
            <p className="text-xs text-red-600 mt-1">{errors[field.name]}</p>
          )}
        </div>
      ))}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Submitting...' : element.data.submitLabel || 'Submit'}
      </button>
    </form>
  );
};

// Action Buttons
const ActionButtons = ({
  element,
  onComplete
}) => {
  const [processing, setProcessing] = useState(null);

  const handleAction = async (action) => {
    setProcessing(action.id);
    try {
      const result = await element.onInteraction('action', {
        actionId: action.id,
        params: action.params
      });
      onComplete?.(result);
    } catch (error) {
      console.error('Action failed:', error);
    } finally {
      setProcessing(null);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {element.data.actions.map((action) => (
        <button
          key={action.id}
          onClick={() => handleAction(action)}
          disabled={processing !== null}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            action.variant === 'primary'
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : action.variant === 'danger'
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          } disabled:opacity-50`}
        >
          {processing === action.id ? (
            <Loader className="w-4 h-4 animate-spin" />
          ) : (
            action.label
          )}
        </button>
      ))}
    </div>
  );
};

export default function InteractiveElements({
  elements,
  onElementComplete
}) {
  const renderElement = (element) => {
    switch (element.type) {
      case 'code':
        return (
          <ExecutableCode
            element={element}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case 'query':
        return (
          <QueryBuilder
            element={element}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case 'decision':
        return (
          <DecisionTree
            element={element}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case 'form':
        return (
          <DynamicForm
            element={element}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case 'action':
        return (
          <ActionButtons
            element={element}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      {elements.map(element => (
        <motion.div
          key={element.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {renderElement(element)}
        </motion.div>
      ))}
    </div>
  );
}
