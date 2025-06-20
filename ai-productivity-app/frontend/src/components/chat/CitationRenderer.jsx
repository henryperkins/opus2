// components/chat/CitationRenderer.jsx
/* global navigator */
import React, { useState, useRef, useEffect } from 'react';
import { FileText, ExternalLink, ChevronDown, Check, Copy, Bookmark } from 'lucide-react';

// Helper function to parse text with citation markers
function parseTextWithCitations(text, citations) {
  const citationRegex = /\[(\d+)\]/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(text)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    // Add citation
    const citationNumber = parseInt(match[1]);
    const citation = citations.find(c => c.number === citationNumber);
    if (citation) {
      parts.push(
        <CitationBadge
          key={`citation-${match.index}`}
          citation={citation}
          inline
        />
      );
    } else {
      parts.push(match[0]); // Keep original if citation not found
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}

function CitationBadge({
  citation,
  inline = false,
  onClick
}) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const badgeRef = useRef(null);
  const tooltipRef = useRef(null);

  useEffect(() => {
    if (showTooltip && badgeRef.current && tooltipRef.current) {
      const badgeRect = badgeRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();

      // Calculate position to keep tooltip in viewport
      let left = badgeRect.left + badgeRect.width / 2 - tooltipRect.width / 2;
      let top = badgeRect.bottom + 8;

      // Adjust if tooltip goes off screen
      if (left < 10) left = 10;
      if (left + tooltipRect.width > window.innerWidth - 10) {
        left = window.innerWidth - tooltipRect.width - 10;
      }
      if (top + tooltipRect.height > window.innerHeight - 10) {
        top = badgeRect.top - tooltipRect.height - 8;
      }

      setPosition({ top, left });
    }
  }, [showTooltip]);

  const confidenceColor = citation.confidence >= 0.8 ? 'blue' :
                          citation.confidence >= 0.6 ? 'yellow' : 'red';

  return (
    <>
      <span
        ref={badgeRef}
        className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium cursor-pointer transition-colors ${
          inline
            ? `bg-${confidenceColor}-100 text-${confidenceColor}-800 hover:bg-${confidenceColor}-200`
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={onClick}
      >
        [{citation.number}]
      </span>

      {showTooltip && (
        <div
          ref={tooltipRef}
          className="fixed z-50 w-80 bg-white rounded-lg shadow-lg border border-gray-200 p-4"
          style={{ top: position.top, left: position.left }}
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-gray-500" />
              <h4 className="text-sm font-medium text-gray-900 truncate">
                {citation.source.title}
              </h4>
            </div>
            <div className={`px-2 py-0.5 rounded-full text-xs bg-${confidenceColor}-100 text-${confidenceColor}-800`}>
              {Math.round(citation.confidence * 100)}%
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
    </>
  );
}

export default function CitationRenderer({
  text,
  citations,
  inline = true,
  onCitationClick
}) {
  const [expandedCitations, setExpandedCitations] = useState(new Set());
  const [copiedCitation, setCopiedCitation] = useState(null);

  const toggleCitation = (citationId) => {
    setExpandedCitations(prev => {
      const newSet = new Set(prev);
      if (newSet.has(citationId)) {
        newSet.delete(citationId);
      } else {
        newSet.add(citationId);
      }
      return newSet;
    });
  };

  const copyCitation = async (citation) => {
    const citationText = `[${citation.number}] ${citation.source.title}. ${citation.source.path}`;
    await navigator.clipboard.writeText(citationText);
    setCopiedCitation(citation.id);
    setTimeout(() => setCopiedCitation(null), 2000);
  };

  if (inline) {
    return (
      <div className="prose prose-sm max-w-none">
        <p>{parseTextWithCitations(text, citations)}</p>
      </div>
    );
  }

  // Footnote style rendering
  return (
    <div className="space-y-4">
      <div className="prose prose-sm max-w-none">
        <p>{parseTextWithCitations(text, citations)}</p>
      </div>

      {citations.length > 0 && (
        <div className="border-t pt-4 mt-6">
          <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
            <Bookmark className="w-4 h-4 mr-2" />
            References
          </h4>
          <div className="space-y-2">
            {citations.map(citation => (
              <div
                key={citation.id}
                className="border border-gray-200 rounded-lg overflow-hidden"
              >
                <div
                  className="px-4 py-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => toggleCitation(citation.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-sm font-medium text-gray-700">
                        [{citation.number}]
                      </span>
                      <div className="flex-1">
                        <h5 className="text-sm font-medium text-gray-900">
                          {citation.source.title}
                        </h5>
                        <p className="text-xs text-gray-600 mt-0.5">
                          {citation.source.path}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`text-xs px-2 py-1 rounded-full bg-${
                        citation.confidence >= 0.8 ? 'blue' :
                        citation.confidence >= 0.6 ? 'yellow' : 'red'
                      }-100 text-${
                        citation.confidence >= 0.8 ? 'blue' :
                        citation.confidence >= 0.6 ? 'yellow' : 'red'
                      }-800`}>
                        {Math.round(citation.confidence * 100)}%
                      </span>
                      <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${
                        expandedCitations.has(citation.id) ? 'rotate-180' : ''
                      }`} />
                    </div>
                  </div>
                </div>

                {expandedCitations.has(citation.id) && (
                  <div className="px-4 py-3 bg-white border-t border-gray-200">
                    <div className="space-y-3">
                      {citation.context && (
                        <div className="text-sm text-gray-700">
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
                              copyCitation(citation);
                            }}
                            className="p-1.5 text-gray-500 hover:text-gray-700 rounded hover:bg-gray-100"
                            title="Copy citation"
                          >
                            {copiedCitation === citation.id ? (
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
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
