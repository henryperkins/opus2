import React from 'react';
import { Brain, CheckCircle, AlertTriangle, XCircle, Circle } from 'lucide-react';

/**
 * Session-wide RAG status badge showing overall RAG activity for the current chat session
 */
const SessionRAGBadge = ({ messages = [], className = '' }) => {
  // Calculate session-wide RAG statistics
  const ragStats = React.useMemo(() => {
    const assistantMessages = messages.filter(msg => msg.role === 'assistant');

    if (assistantMessages.length === 0) {
      return {
        totalMessages: 0,
        ragActiveCount: 0,
        avgConfidence: 0,
        status: 'standard',
        lastRAGStatus: null
      };
    }

    // Only count messages where RAG was actually used (ragUsed is true)
    const ragActiveMessages = assistantMessages.filter(msg =>
      msg.metadata?.ragUsed === true && msg.metadata?.ragConfidence > 0
    );

    // Calculate total confidence only from messages where RAG was actually used
    const totalConfidence = ragActiveMessages.reduce((sum, msg) =>
      sum + (msg.metadata?.ragConfidence || 0), 0
    );

    const avgConfidence = ragActiveMessages.length > 0
      ? totalConfidence / ragActiveMessages.length
      : 0;

    // Get the most recent message's RAG status
    const lastMessage = assistantMessages[assistantMessages.length - 1];
    const lastRAGStatus = lastMessage?.metadata?.ragStatus;

    // Determine overall session status based on actual RAG usage
    let status = 'standard';

    // Only set to 'active' if there are actually messages using RAG
    if (ragActiveMessages.length > 0) {
      // Set to active only if the average confidence is acceptable
      if (avgConfidence >= 0.6) {
        status = 'active';
      } else {
        status = 'degraded';
      }
    }

    // Override with error status if last message had an error
    if (lastRAGStatus === 'error') {
      status = 'error';
    }

    return {
      totalMessages: assistantMessages.length,
      ragActiveCount: ragActiveMessages.length,
      avgConfidence,
      status,
      lastRAGStatus,
      ragUsagePercent: assistantMessages.length > 0
        ? (ragActiveMessages.length / assistantMessages.length) * 100
        : 0
    };
  }, [messages]);

  const getStatusConfig = () => {
    switch (ragStats.status) {
      case 'active':
        // Use confidence level to differentiate between "excellent" and "good" active states
        if (ragStats.avgConfidence >= 0.8) {
          return {
            icon: <CheckCircle className="w-4 h-4" />,
            bgColor: 'bg-green-100',
            textColor: 'text-green-800',
            borderColor: 'border-green-200',
            label: 'RAG Excellent',
            description: `${Math.round(ragStats.avgConfidence * 100)}% avg confidence`
          };
        } else {
          return {
            icon: <CheckCircle className="w-4 h-4" />,
            bgColor: 'bg-blue-100',
            textColor: 'text-blue-800',
            borderColor: 'border-blue-200',
            label: 'RAG Active',
            description: `${Math.round(ragStats.avgConfidence * 100)}% avg confidence`
          };
        }
      case 'degraded':
        return {
          icon: <AlertTriangle className="w-4 h-4" />,
          bgColor: 'bg-yellow-100',
          textColor: 'text-yellow-800',
          borderColor: 'border-yellow-200',
          label: 'RAG Limited',
          description: `${Math.round(ragStats.avgConfidence * 100)}% avg confidence`
        };
      case 'error':
        return {
          icon: <XCircle className="w-4 h-4" />,
          bgColor: 'bg-red-100',
          textColor: 'text-red-800',
          borderColor: 'border-red-200',
          label: 'RAG Error',
          description: 'Knowledge access issues'
        };
      default:
        return {
          icon: <Circle className="w-4 h-4" />,
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-800',
          borderColor: 'border-gray-200',
          label: 'RAG Ready',
          description: 'Knowledge sources available'
        };
    }
  };

  const statusConfig = getStatusConfig();

  // Don't show if no messages yet
  if (ragStats.totalMessages === 0) {
    return null;
  }

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${statusConfig.bgColor} ${statusConfig.textColor} ${statusConfig.borderColor} ${className}`}>
      <Brain className="w-4 h-4" />
      {statusConfig.icon}

      <div className="flex flex-col">
        <span className="text-xs font-semibold">{statusConfig.label}</span>
        <span className="text-xs opacity-80">{statusConfig.description}</span>
      </div>

      {/* Usage statistics */}
      <div className="ml-2 text-xs opacity-75">
        {ragStats.ragActiveCount}/{ragStats.totalMessages}
      </div>
    </div>
  );
};

export default SessionRAGBadge;
