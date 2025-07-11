// components/chat/InteractiveElements.jsx
import React, { useState, useCallback } from "react";
import {
  Play,
  Code,
  FileText,
  Download,
  ChevronRight,
  ChevronDown,
  Check,
  X,
  AlertCircle,
  Loader,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// Executable Code Block
const ExecutableCode = ({ element, onComplete }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);

  const handleRun = async () => {
    setIsRunning(true);
    setOutput(null);
    setError(null);

    try {
      const result = await element.onInteraction("run", {
        code: element.data.code,
        language: element.data.language,
      });

      setOutput(result.output);
      onComplete?.(result);
    } catch (err) {
      setError(err.message || "Execution failed");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="bg-gray-100 dark:bg-gray-800 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Code className="w-4 h-4 text-gray-600" />
          <span className="text-sm font-medium">{element.data.language}</span>
        </div>
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
          <span>{isRunning ? "Running..." : "Run"}</span>
        </button>
      </div>

      <pre className="p-4 bg-gray-50 dark:bg-gray-900 overflow-x-auto">
        <code className="text-sm">{element.data.code}</code>
      </pre>

      <AnimatePresence>
        {(output || error) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t"
          >
            <div
              className={`p-4 ${error ? "bg-red-50 dark:bg-red-900/20" : "bg-green-50 dark:bg-green-900/20"}`}
            >
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
const QueryBuilder = ({ element, onComplete }) => {
  const [query, setQuery] = useState(element.data.initialQuery || "");
  const [filters, setFilters] = useState(element.data.filters || {});
  const [isExecuting, setIsExecuting] = useState(false);
  const [results, setResults] = useState(null);

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      const result = await element.onInteraction("execute", { query, filters });
      setResults(result.data);
      onComplete?.(result);
    } catch (error) {
      console.error("Query execution failed:", error);
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

      {Object.keys(element.data.availableFilters || {}).map((filterKey) => (
        <div key={filterKey}>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {element.data.availableFilters[filterKey].label}
          </label>
          <input
            type={element.data.availableFilters[filterKey].type || "text"}
            value={filters[filterKey] || ""}
            onChange={(e) =>
              setFilters({ ...filters, [filterKey]: e.target.value })
            }
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
        {isExecuting ? "Executing..." : "Execute Query"}
      </button>

      {results && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h4 className="text-sm font-medium mb-2">
            Results ({results.length})
          </h4>
          <pre className="text-xs overflow-x-auto">
            {JSON.stringify(results, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

// Decision Tree
const DecisionTree = ({ element, onComplete }) => {
  const [currentNode, setCurrentNode] = useState(element.data.root);
  const [path, setPath] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleChoice = async (choice) => {
    setIsProcessing(true);
    const newPath = [...path, choice.label];
    setPath(newPath);

    try {
      const result = await element.onInteraction("choose", {
        nodeId: currentNode.id,
        choice: choice.value,
        path: newPath,
      });

      if (result.nextNode) {
        setCurrentNode(result.nextNode);
      } else {
        onComplete?.(result);
      }
    } catch (error) {
      console.error("Decision processing failed:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBack = () => {
    if (path.length > 0) {
      const newPath = path.slice(0, -1);
      setPath(newPath);
      // Would need to reconstruct the node from path
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
            Path: {path.join(" → ")}
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
                    <div className="text-xs text-gray-600 mt-1">
                      {choice.description}
                    </div>
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
const DynamicForm = ({ element, onComplete }) => {
  const [formData, setFormData] = useState(element.data.initialValues || {});
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrors({});

    try {
      const result = await element.onInteraction("submit", formData);
      onComplete?.(result);
    } catch (error) {
      if (error.validationErrors) {
        setErrors(error.validationErrors);
      } else {
        console.error("Form submission failed:", error);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setFormData({ ...formData, [fieldName]: value });
    // Clear error for this field
    if (errors[fieldName]) {
      setErrors({ ...errors, [fieldName]: "" });
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

          {field.type === "select" ? (
            <select
              value={formData[field.name] || ""}
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
          ) : field.type === "textarea" ? (
            <textarea
              value={formData[field.name] || ""}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              rows={field.rows || 3}
              required={field.required}
              placeholder={field.placeholder}
            />
          ) : (
            <input
              type={field.type || "text"}
              value={formData[field.name] || ""}
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
        {isSubmitting ? "Submitting..." : element.data.submitLabel || "Submit"}
      </button>
    </form>
  );
};

// Action Buttons
const ActionButtons = ({ element, onComplete }) => {
  const [processing, setProcessing] = useState(null);

  const handleAction = async (action) => {
    setProcessing(action.id);
    try {
      const result = await element.onInteraction("action", {
        actionId: action.id,
        params: action.params,
      });
      onComplete?.(result);
    } catch (error) {
      console.error("Action failed:", error);
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
            action.variant === "primary"
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : action.variant === "danger"
                ? "bg-red-600 text-white hover:bg-red-700"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
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
  onElementComplete,
  codeExecutor,
}) {
  // Create interaction handler for elements
  const createInteractionHandler = (elementId) => async (action, data) => {
    try {
      // Handle different interaction types
      switch (action) {
        case "run":
          // For code execution, use the real code executor if provided
          if (data.code && data.language && codeExecutor) {
            try {
              const result = await codeExecutor(
                data.code,
                data.language,
                elementId,
              );
              return {
                output: result.output || "",
                error: result.error || null,
                execution_time: result.execution_time || 0,
                type: "code_execution",
              };
            } catch (error) {
              return {
                output: "",
                error: error.message || "Code execution failed",
                execution_time: 0,
                type: "code_execution",
              };
            }
          } else if (data.code && data.language) {
            // Fallback for when no executor is provided
            return {
              output: `// Code execution not configured\n// Code: ${data.code.substring(0, 100)}...`,
              error: null,
              execution_time: 0.1,
              type: "code_execution",
            };
          }
          break;

        case "submit":
          // For form submissions
          return {
            success: true,
            message: "Form submitted successfully",
            type: "form_submission",
            data: data,
          };

        case "select":
          // For decision tree selections
          return {
            success: true,
            selection: data.selectedOption,
            type: "decision_made",
            data: data,
          };

        case "build":
          // For query builder
          return {
            success: true,
            query: data.query,
            type: "query_built",
            data: data,
          };

        case "action":
          // For action buttons
          return {
            success: true,
            actionId: data.actionId,
            type: "action_triggered",
            data: data,
          };

        default:
          return {
            success: true,
            message: `Action ${action} completed`,
            type: "generic_interaction",
            action: action,
            data: data,
          };
      }
    } catch (error) {
      return {
        error: error.message || "Interaction failed",
      };
    }
  };

  const renderElement = (element) => {
    // Inject the interaction handler into the element
    const elementWithInteraction = {
      ...element,
      onInteraction: createInteractionHandler(element.id),
    };

    switch (element.type) {
      case "code":
        return (
          <ExecutableCode
            element={elementWithInteraction}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case "query":
        return (
          <QueryBuilder
            element={elementWithInteraction}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case "decision":
        return (
          <DecisionTree
            element={elementWithInteraction}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case "form":
        return (
          <DynamicForm
            element={elementWithInteraction}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      case "action":
        return (
          <ActionButtons
            element={elementWithInteraction}
            onComplete={(result) => onElementComplete?.(element.id, result)}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      {elements.map((element) => (
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
