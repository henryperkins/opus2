// components/analytics/ResponseQuality.jsx
import { useState, useMemo } from 'react';
import {
  ThumbsUp, ThumbsDown, MessageSquare,
  Clock, Zap, AlertCircle
} from 'lucide-react';
import PropTypes from 'prop-types';

// Quality assessment algorithms
const assessQuality = (content, metadata) => {
  // Relevance - based on context and citations
  const relevance = metadata?.citations?.length > 0 ? 0.9 : 0.7;

  // Accuracy - placeholder, would need fact-checking
  const accuracy = 0.85;

  // Helpfulness - based on structure and content
  const hasStructure = content.includes('•') || content.includes('1.') || content.includes('##');
  const hasCode = content.includes('```');
  const hasExplanation = content.length > 200;
  const helpfulness = (hasStructure ? 0.3 : 0) + (hasCode ? 0.3 : 0) + (hasExplanation ? 0.4 : 0);

  // Clarity - based on readability
  const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
  const avgSentenceLength = sentences.reduce((sum, s) => sum + s.split(' ').length, 0) / sentences.length;
  const clarity = avgSentenceLength < 20 ? 0.9 : avgSentenceLength < 30 ? 0.7 : 0.5;

  // Completeness - based on length and structure
  const completeness = Math.min(content.length / 500, 1) * 0.7 + (hasStructure ? 0.3 : 0);

  // Other metrics
  const citations = metadata?.citations?.length || 0;
  const responseTime = metadata?.responseTime || 2000;
  const tokenCount = metadata?.tokens?.completion || Math.ceil(content.length / 4);

  return {
    relevance,
    accuracy,
    helpfulness,
    clarity,
    completeness,
    citations,
    responseTime,
    tokenCount
  };
};

const MetricBar = ({
  label,
  value,
  color = 'blue'
}) => {
  const percentage = Math.round(value * 100);
  const colorClass = {
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500'
  }[color] || 'bg-blue-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

MetricBar.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired,
  color: PropTypes.string
};

export default function ResponseQuality({
  content,
  metadata,
  onFeedback,
  showDetailedMetrics = false
}) {
  const [userRating, setUserRating] = useState(null);
  const [showMetrics, setShowMetrics] = useState(false);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);

  const metrics = useMemo(() => assessQuality(content, metadata), [content, metadata]);

  const overallScore = useMemo(() => {
    const weights = {
      relevance: 0.3,
      accuracy: 0.25,
      helpfulness: 0.2,
      clarity: 0.15,
      completeness: 0.1
    };

    return Object.entries(weights).reduce((score, [key, weight]) => {
      return score + (metrics[key] || 0) * weight;
    }, 0);
  }, [metrics]);

  const handleRating = (rating) => {
    setUserRating(rating);

    if (rating === 'negative') {
      setShowFeedbackForm(true);
    } else {
      onFeedback?.({
        rating,
        timestamp: new Date(),
        userId: 'current-user' // Would get from auth context
      });
    }
  };

  const handleSubmitFeedback = () => {
    if (userRating) {
      onFeedback?.({
        rating: userRating,
        comment: feedbackComment,
        timestamp: new Date(),
        userId: 'current-user'
      });
      setShowFeedbackForm(false);
      setFeedbackComment('');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'green';
    if (score >= 0.6) return 'yellow';
    return 'red';
  };

  const getScoreLabel = (score) => {
    if (score >= 0.8) return 'Excellent';
    if (score >= 0.6) return 'Good';
    if (score >= 0.4) return 'Fair';
    return 'Poor';
  };

  return (
    <div className="space-y-3">
      {/* Quick Actions Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {/* Rating Buttons */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleRating('positive')}
              className={`p-1.5 rounded transition-colors ${
                userRating === 'positive'
                  ? 'bg-green-100 text-green-600'
                  : 'text-gray-400 hover:text-green-600'
              }`}
              title="Helpful"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleRating('negative')}
              className={`p-1.5 rounded transition-colors ${
                userRating === 'negative'
                  ? 'bg-red-100 text-red-600'
                  : 'text-gray-400 hover:text-red-600'
              }`}
              title="Not helpful"
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>

          {/* Quality Score */}
          <div className="flex items-center space-x-2">
            <div className={`text-sm font-medium text-${getScoreColor(overallScore)}-600`}>
              {getScoreLabel(overallScore)}
            </div>
            <button
              onClick={() => setShowMetrics(!showMetrics)}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              {showMetrics ? 'Hide' : 'Show'} details
            </button>
          </div>
        </div>

        {/* Meta Info */}
        <div className="flex items-center space-x-3 text-xs text-gray-500">
          {metadata?.model && (
            <span className="flex items-center space-x-1">
              <Zap className="w-3 h-3" />
              <span>{metadata.model}</span>
            </span>
          )}
          {metadata?.responseTime && (
            <span className="flex items-center space-x-1">
              <Clock className="w-3 h-3" />
              <span>{(metadata.responseTime / 1000).toFixed(1)}s</span>
            </span>
          )}
          {metadata?.tokens && (
            <span className="flex items-center space-x-1">
              <MessageSquare className="w-3 h-3" />
              <span>{metadata.tokens.completion} tokens</span>
            </span>
          )}
        </div>
      </div>

      {/* Detailed Metrics */}
      {showMetrics && (
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricBar
              label="Relevance"
              value={metrics.relevance}
              color={getScoreColor(metrics.relevance)}
            />
            <MetricBar
              label="Accuracy"
              value={metrics.accuracy}
              color={getScoreColor(metrics.accuracy)}
            />
            <MetricBar
              label="Helpfulness"
              value={metrics.helpfulness}
              color={getScoreColor(metrics.helpfulness)}
            />
            <MetricBar
              label="Clarity"
              value={metrics.clarity}
              color={getScoreColor(metrics.clarity)}
            />
            <MetricBar
              label="Completeness"
              value={metrics.completeness}
              color={getScoreColor(metrics.completeness)}
            />
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-600">Citations</span>
              <span className="font-medium">{metrics.citations}</span>
            </div>
          </div>

          {showDetailedMetrics && (
            <div className="pt-3 border-t space-y-2">
              <h4 className="text-xs font-medium text-gray-700">Performance Metrics</h4>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {(metrics.responseTime / 1000).toFixed(1)}s
                  </div>
                  <div className="text-gray-600">Response Time</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {metrics.tokenCount}
                  </div>
                  <div className="text-gray-600">Tokens Used</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    ${((metrics.tokenCount / 1000) * 0.002).toFixed(3)}
                  </div>
                  <div className="text-gray-600">Est. Cost</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Feedback Form */}
      {showFeedbackForm && (
        <div className="bg-yellow-50 rounded-lg p-4 space-y-3">
          <div className="flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-900">
                Help us improve
              </h4>
              <textarea
                value={feedbackComment}
                onChange={(e) => setFeedbackComment(e.target.value)}
                placeholder="What could be better about this response?"
                className="mt-2 w-full px-3 py-2 border rounded-lg text-sm"
                rows={3}
              />
              <div className="mt-2 flex justify-end space-x-2">
                <button
                  onClick={() => {
                    setShowFeedbackForm(false);
                    setUserRating(null);
                  }}
                  className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmitFeedback}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Submit Feedback
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

ResponseQuality.propTypes = {
  content: PropTypes.string.isRequired,
  metadata: PropTypes.shape({
    model: PropTypes.string,
    responseTime: PropTypes.number,
    tokens: PropTypes.shape({
      completion: PropTypes.number
    }),
    citations: PropTypes.array
  }),
  onFeedback: PropTypes.func,
  showDetailedMetrics: PropTypes.bool
};