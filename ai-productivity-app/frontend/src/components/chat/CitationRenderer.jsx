import { useState } from 'react';
import { copyToClipboard } from '../../utils/clipboard';
// eslint-disable-next-line no-unused-vars
import { FileText, ExternalLink, ChevronDown, Check, Copy, Bookmark } from 'lucide-react';
import PropTypes from 'prop-types';

// Confidence level utilities
const getConfidenceClass = (confidence) => {
  if (confidence >= 0.8) return 'bg-blue-100 text-blue-800';
  if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
};

const getConfidenceText = (confidence) => `${Math.round(confidence * 100)}%`;

// Simple tooltip component
function Tooltip({ children, citation }) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      >
        {children}
      </div>

      {show && (
        <div className="absolute z-50 w-80 p-4 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg left-1/2 transform -translate-x-1/2">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-2 flex-1 min-w-0">
              <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
              <h4 className="text-sm font-medium text-gray-900 truncate">
                {citation.source.title}
              </h4>
            </div>
            <div className={`px-2 py-0.5 rounded-full text-xs flex-shrink-0 ml-2 ${getConfidenceClass(citation.confidence)}`}>
              {getConfidenceText(citation.confidence)}
            </div>
          </div>

          <p className="text-xs text-gray-600 mb-2">{citation.source.path}</p>

          <div className="text-sm text-gray-700 bg-gray-50 p-2 rounded mb-2">
            "{citation.content.slice(0, 150)}..."
          </div>

          {citation.source.author && (
            <p className="text-xs text-gray-500">By {citation.source.author}</p>
          )}
        </div>
      )}
    </div>
  );
}

Tooltip.propTypes = {
  children: PropTypes.node.isRequired,
  citation: PropTypes.shape({
    source: PropTypes.shape({
      title: PropTypes.string.isRequired,
      path: PropTypes.string.isRequired,
      author: PropTypes.string
    }).isRequired,
    confidence: PropTypes.number.isRequired,
    content: PropTypes.string.isRequired
  }).isRequired
};

// Citation badge component
function CitationBadge({ citation, onClick }) {
  const baseClass = "inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium cursor-pointer transition-colors";
  const colorClass = getConfidenceClass(citation.confidence);

  return (
    <Tooltip citation={citation}>
      <span
        className={`${baseClass} ${colorClass} hover:opacity-80`}
        onClick={onClick}
      >
        [{citation.number}]
      </span>
    </Tooltip>
  );
}

CitationBadge.propTypes = {
  citation: PropTypes.shape({
    number: PropTypes.number.isRequired,
    confidence: PropTypes.number.isRequired,
    source: PropTypes.shape({
      title: PropTypes.string.isRequired,
      path: PropTypes.string.isRequired,
      author: PropTypes.string
    }).isRequired,
    content: PropTypes.string.isRequired
  }).isRequired,
  onClick: PropTypes.func
};

// Text parser for citations
function parseTextWithCitations(text, citations, onCitationClick) {
  const citationRegex = /\[(\d+)\]/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const citationNumber = parseInt(match[1]);
    const citation = citations.find(c => c.number === citationNumber);

    if (citation) {
      parts.push(
        <CitationBadge
          key={`citation-${match.index}`}
          citation={citation}
          onClick={() => onCitationClick?.(citation)}
        />
      );
    } else {
      parts.push(match[0]);
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}


function formatCitation(citation) {
  return `[${citation.number}] ${citation.source.title}. ${citation.source.path}`;
}

// Citation list component
function CitationList({ citations, onCitationClick }) {
  const [expanded, setExpanded] = useState(new Set());
  const [copied, setCopied] = useState(null);

  const toggleExpanded = (id) => {
    setExpanded(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleCopy = async (citation) => {
    const success = await copyToClipboard(formatCitation(citation));
    if (success) {
      setCopied(citation.id);
      // eslint-disable-next-line no-undef
      setTimeout(() => setCopied(null), 2000);
    }
  };

  return (
    <div className="border-t pt-4 mt-6">
      <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
        <Bookmark className="w-4 h-4 mr-2" />
        References
      </h4>

      <div className="space-y-2">
        {citations.map(citation => {
          const isExpanded = expanded.has(citation.id);
          const isCopied = copied === citation.id;

          return (
            <div key={citation.id} className="border border-gray-200 rounded-lg overflow-hidden">
              <div
                className="px-4 py-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => toggleExpanded(citation.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <span className="text-sm font-medium text-gray-700">
                      [{citation.number}]
                    </span>
                    <div className="flex-1 min-w-0">
                      <h5 className="text-sm font-medium text-gray-900 truncate">
                        {citation.source.title}
                      </h5>
                      <p className="text-xs text-gray-600 mt-0.5 truncate">
                        {citation.source.path}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceClass(citation.confidence)}`}>
                      {getConfidenceText(citation.confidence)}
                    </span>
                    <ChevronDown
                      className={`w-4 h-4 text-gray-500 transition-transform ${
                        isExpanded ? 'rotate-180' : ''
                      }`}
                    />
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="px-4 py-3 bg-white border-t border-gray-200">
                  {citation.context && (
                    <div className="text-sm text-gray-700 mb-3">
                      {citation.context.before && (
                        <span className="text-gray-500">...{citation.context.before}</span>
                      )}
                      <span className="bg-yellow-100 px-1">{citation.content}</span>
                      {citation.context.after && (
                        <span className="text-gray-500">{citation.context.after}...</span>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <div className="text-xs text-gray-500">
                      {citation.source.author && <span>By {citation.source.author} • </span>}
                      {citation.source.lastModified && <span>Modified {citation.source.lastModified}</span>}
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopy(citation);
                        }}
                        className="p-1.5 text-gray-500 hover:text-gray-700 rounded hover:bg-gray-100"
                        title="Copy citation"
                      >
                        {isCopied ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onCitationClick?.(citation);
                        }}
                        className="p-1.5 text-gray-500 hover:text-gray-700 rounded hover:bg-gray-100"
                        title="Open source"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

CitationList.propTypes = {
  citations: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    number: PropTypes.number.isRequired,
    source: PropTypes.shape({
      title: PropTypes.string.isRequired,
      path: PropTypes.string.isRequired,
      author: PropTypes.string,
      lastModified: PropTypes.string
    }).isRequired,
    content: PropTypes.string.isRequired,
    confidence: PropTypes.number.isRequired,
    context: PropTypes.shape({
      before: PropTypes.string,
      after: PropTypes.string
    })
  })).isRequired,
  onCitationClick: PropTypes.func
};

// Main component
export default function CitationRenderer({
  text,
  citations = [],
  inline = true,
  onCitationClick
}) {
  if (inline) {
    return (
      <div className="prose prose-sm max-w-none">
        <p>{parseTextWithCitations(text, citations, onCitationClick)}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="prose prose-sm max-w-none">
        <p>{parseTextWithCitations(text, citations, onCitationClick)}</p>
      </div>

      {citations.length > 0 && (
        <CitationList
          citations={citations}
          onCitationClick={onCitationClick}
        />
      )}
    </div>
  );
}

CitationRenderer.propTypes = {
  text: PropTypes.string.isRequired,
  citations: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    number: PropTypes.number.isRequired,
    source: PropTypes.shape({
      title: PropTypes.string.isRequired,
      path: PropTypes.string.isRequired,
      author: PropTypes.string
    }).isRequired,
    content: PropTypes.string.isRequired,
    confidence: PropTypes.number.isRequired
  })),
  inline: PropTypes.bool,
  onCitationClick: PropTypes.func
};
