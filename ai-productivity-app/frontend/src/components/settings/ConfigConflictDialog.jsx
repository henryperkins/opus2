// frontend/src/components/settings/ConfigConflictDialog.jsx
import React, { useState } from "react";
import PropTypes from "prop-types";
import { useAIConfig } from "../../contexts/AIConfigContext";
import { AlertTriangle, X, Check, AlignCenter } from "lucide-react";

/**
 * Modal dialog that appears when the backend reports a *configuration
 * conflict* via WebSocket.  The dialog presents both versions as JSON diff
 * (simplified) and offers three resolution strategies:
 *   • Merge – let the server intelligently merge non-conflicting keys.
 *   • Overwrite – force apply *my* proposed config.
 *   • Abort – discard my changes.
 */
export default function ConfigConflictDialog({ className = "" }) {
  const { conflictState, resolveConflict, resetError } = useAIConfig();

  const [submitting, setSubmitting] = useState(false);

  if (!conflictState) return null;

  const {
    current_config: currentCfg,
    proposed_config: proposedCfg,
    conflicts,
  } = conflictState;

  const handleResolve = async (strategy) => {
    setSubmitting(true);
    try {
      await resolveConflict(strategy, proposedCfg);
    } finally {
      setSubmitting(false);
    }
  };

  const close = () => {
    // Keep conflictState but hide dialog – or fully reset?
    // For now we reset to avoid stale state.
    // Dispatch global CLEAR_CONFLICT action
    resetError();
  };

  const pretty = (obj) => JSON.stringify(obj, null, 2);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm ${className}`}
    >
      <div className="bg-white dark:bg-gray-800 w-full max-w-3xl rounded-lg shadow-lg p-6 relative">
        <button
          onClick={close}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-6 w-6 text-yellow-500" />
          <h2 className="text-lg font-semibold">
            Configuration conflict detected
          </h2>
        </div>

        <p className="text-sm mb-4 text-gray-700 dark:text-gray-300">
          Another user changed the AI configuration at the same time. Choose how
          to proceed.
        </p>

        {/* Simple side-by-side diff */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <h3 className="font-medium mb-1 flex items-center gap-1">
              <AlignCenter className="h-3 w-3" /> Current
            </h3>
            <pre className="bg-gray-100 dark:bg-gray-900 rounded p-2 overflow-auto max-h-60 whitespace-pre-wrap">
              {pretty(currentCfg)}
            </pre>
          </div>
          <div>
            <h3 className="font-medium mb-1 flex items-center gap-1">
              <AlignCenter className="h-3 w-3" /> Yours
            </h3>
            <pre className="bg-gray-100 dark:bg-gray-900 rounded p-2 overflow-auto max-h-60 whitespace-pre-wrap">
              {pretty(proposedCfg)}
            </pre>
          </div>
        </div>

        {conflicts?.length ? (
          <div className="mt-4 text-sm text-red-600 dark:text-red-400">
            <p className="font-medium">Conflicting fields:</p>
            <ul className="list-disc list-inside">
              {conflicts.map((c) => (
                <li key={`${c.field}-${c.severity}`}>{c.field}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {/* Actions */}
        <div className="mt-6 flex flex-col md:flex-row gap-3 justify-end">
          <button
            onClick={() => handleResolve("abort")}
            disabled={submitting}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel my changes
          </button>
          <button
            onClick={() => handleResolve("merge")}
            disabled={submitting}
            className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:opacity-50"
          >
            Merge non-conflicting
          </button>
          <button
            onClick={() => handleResolve("overwrite")}
            disabled={submitting}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
          >
            <Check className="h-4 w-4" /> Apply my version
          </button>
        </div>
      </div>
    </div>
  );
}

ConfigConflictDialog.propTypes = {
  className: PropTypes.string,
};
