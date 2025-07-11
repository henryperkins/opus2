import React, { useState } from "react";
import { AlertTriangle, Info, Eye, EyeOff, Shield } from "lucide-react";

const ConfidenceWarning = ({ warnings, ragMetadata, className = "" }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!warnings || warnings.length === 0) {
    return null;
  }

  const getWarningIcon = (warning) => {
    if (warning.includes("⚠️")) {
      return <AlertTriangle size={16} className="text-amber-500" />;
    } else if (warning.includes("ℹ️")) {
      return <Info size={16} className="text-blue-500" />;
    } else if (warning.includes("Content Filtered")) {
      return <Shield size={16} className="text-green-500" />;
    }
    return <Info size={16} className="text-gray-500" />;
  };

  const getWarningLevel = (warnings) => {
    if (
      warnings.some(
        (w) => w.includes("Low Confidence") || w.includes("No Sources"),
      )
    ) {
      return "high";
    } else if (
      warnings.some(
        (w) =>
          w.includes("Moderate Confidence") || w.includes("Limited Sources"),
      )
    ) {
      return "medium";
    }
    return "low";
  };

  const warningLevel = getWarningLevel(warnings);

  const levelStyles = {
    high: "bg-red-50 border-red-200 text-red-800",
    medium: "bg-amber-50 border-amber-200 text-amber-800",
    low: "bg-blue-50 border-blue-200 text-blue-800",
  };

  const cleanWarningText = (warning) => {
    // Remove emoji indicators and markdown formatting
    return warning.replace(/^[⚠️ℹ️]+\s*\*?\*?/, "").replace(/\*\*/g, "");
  };

  return (
    <div
      className={`${levelStyles[warningLevel]} border rounded-lg p-3 mt-2 ${className}`}
    >
      <div className="flex items-start gap-2">
        {getWarningIcon(warnings[0])}
        <div className="flex-1 min-w-0">
          {/* Primary Warning */}
          <div className="text-sm font-medium">
            {cleanWarningText(warnings[0])}
          </div>

          {/* Additional Warnings (if collapsed) */}
          {warnings.length > 1 && !isExpanded && (
            <div className="text-xs opacity-75 mt-1">
              +{warnings.length - 1} more{" "}
              {warnings.length === 2 ? "notice" : "notices"}
            </div>
          )}

          {/* All Warnings (if expanded) */}
          {isExpanded && warnings.length > 1 && (
            <div className="mt-2 space-y-1">
              {warnings.slice(1).map((warning, index) => (
                <div key={index} className="flex items-start gap-2 text-sm">
                  {getWarningIcon(warning)}
                  <span>{cleanWarningText(warning)}</span>
                </div>
              ))}
            </div>
          )}

          {/* RAG Metadata (if expanded) */}
          {isExpanded && ragMetadata && (
            <div className="mt-3 pt-2 border-t border-current border-opacity-20">
              <div className="text-xs space-y-1">
                {ragMetadata.rag_confidence !== undefined && (
                  <div>
                    Confidence: {(ragMetadata.rag_confidence * 100).toFixed(0)}%
                  </div>
                )}
                {ragMetadata.knowledge_sources_count !== undefined && (
                  <div>Sources: {ragMetadata.knowledge_sources_count}</div>
                )}
                {ragMetadata.rag_status &&
                  ragMetadata.rag_status !== "standard" && (
                    <div>Status: {ragMetadata.rag_status}</div>
                  )}
              </div>
            </div>
          )}
        </div>

        {/* Expand/Collapse Button */}
        {(warnings.length > 1 || ragMetadata) && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-black hover:bg-opacity-10 rounded"
            title={isExpanded ? "Show less" : "Show more details"}
          >
            {isExpanded ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        )}
      </div>
    </div>
  );
};

export default ConfidenceWarning;
