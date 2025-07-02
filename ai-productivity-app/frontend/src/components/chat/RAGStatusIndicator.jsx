import { Brain, Database, Search, AlertCircle } from 'lucide-react';
import PropTypes from 'prop-types';

// Confidence level utilities
const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
  if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-orange-600 bg-orange-50 border-orange-200';
};

const getConfidenceText = (confidence) => `${Math.round(confidence * 100)}%`;

// RAG status types
const RAG_STATUS_TYPES = {
  ACTIVE: 'active',
  STANDARD: 'standard', 
  DEGRADED: 'degraded',
  POOR: 'poor',
  ERROR: 'error',
  INACTIVE: 'inactive'
};

/**
 * Component to display RAG (Retrieval-Augmented Generation) status for chat messages
 */
const RAGStatusIndicator = ({ 
  ragUsed = false, 
  sourcesCount = 0, 
  confidence = 0, 
  searchQuery = null,
  contextTokensUsed = 0,
  status = RAG_STATUS_TYPES.STANDARD,
  errorMessage = null,
  compact = false 
}) => {
  // Don't show indicator if RAG wasn't used and there's no error or inactive status
  if (!ragUsed && status !== RAG_STATUS_TYPES.ERROR && status !== RAG_STATUS_TYPES.INACTIVE) {
    return null;
  }

  const getStatusIcon = () => {
    switch (status) {
      case RAG_STATUS_TYPES.ACTIVE:
        return <Brain className="w-3 h-3" />;
      case RAG_STATUS_TYPES.DEGRADED:
        return <AlertCircle className="w-3 h-3" />;
      case RAG_STATUS_TYPES.POOR:
        return <AlertCircle className="w-3 h-3" />;
      case RAG_STATUS_TYPES.ERROR:
        return <AlertCircle className="w-3 h-3" />;
      case RAG_STATUS_TYPES.INACTIVE:
        return <Database className="w-3 h-3 opacity-50" />;
      default:
        return <Search className="w-3 h-3" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case RAG_STATUS_TYPES.ACTIVE:
        return confidence ? getConfidenceColor(confidence) : 'text-blue-600 bg-blue-50 border-blue-200';
      case RAG_STATUS_TYPES.DEGRADED:
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case RAG_STATUS_TYPES.POOR:
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case RAG_STATUS_TYPES.ERROR:
        return 'text-red-600 bg-red-50 border-red-200';
      case RAG_STATUS_TYPES.INACTIVE:
        return 'text-gray-500 bg-gray-50 border-gray-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case RAG_STATUS_TYPES.ACTIVE:
        return ragUsed ? `RAG Active (${sourcesCount} source${sourcesCount !== 1 ? 's' : ''})` : 'RAG Active';
      case RAG_STATUS_TYPES.DEGRADED:
        return 'RAG Degraded';
      case RAG_STATUS_TYPES.POOR:
        return 'RAG Poor Quality';
      case RAG_STATUS_TYPES.ERROR:
        return 'RAG Error';
      case RAG_STATUS_TYPES.INACTIVE:
        return 'RAG Disabled';
      default:
        return 'Standard Response';
    }
  };

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        <div className={`w-2 h-2 rounded-full ${ragUsed ? 'bg-green-500' : 'bg-gray-400'}`} />
        {ragUsed && confidence > 0 && (
          <span className="text-xs text-gray-600">
            {getConfidenceText(confidence)}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm ${getStatusColor()}`}>
      <div className="flex items-center gap-1.5">
        {getStatusIcon()}
        <span className="font-medium">{getStatusText()}</span>
      </div>
      
      {ragUsed && (
        <div className="flex items-center gap-3 text-xs opacity-90">
          {confidence > 0 && (
            <span className="font-medium">
              {getConfidenceText(confidence)} confidence
            </span>
          )}
          
          {contextTokensUsed > 0 && (
            <div className="flex items-center gap-1">
              <Database className="w-3 h-3" />
              <span>{contextTokensUsed.toLocaleString()} tokens</span>
            </div>
          )}
        </div>
      )}
      
      {errorMessage && (
        <span className="text-xs opacity-90">
          {errorMessage}
        </span>
      )}
    </div>
  );
};

RAGStatusIndicator.propTypes = {
  ragUsed: PropTypes.bool,
  sourcesCount: PropTypes.number,
  confidence: PropTypes.number,
  searchQuery: PropTypes.string,
  contextTokensUsed: PropTypes.number,
  status: PropTypes.oneOf(Object.values(RAG_STATUS_TYPES)),
  errorMessage: PropTypes.string,
  compact: PropTypes.bool
};

RAGStatusIndicator.RAG_STATUS_TYPES = RAG_STATUS_TYPES;

export default RAGStatusIndicator;