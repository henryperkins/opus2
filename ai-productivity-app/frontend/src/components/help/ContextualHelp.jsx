import React, { useState, useRef } from 'react';
import { HelpCircle, Info, ExternalLink } from 'lucide-react';

// Simple tooltip content for quick help with documentation links
const TOOLTIP_CONTENT = {
  'search-modes': {
    title: "Search Modes",
    content: "Semantic (by meaning), Keyword (exact text), Structural (code patterns), or Hybrid (all modes).",
    docTab: "search",
    docLabel: "View Search Guide"
  },
  'rag-status': {
    title: "RAG Status",
    content: "Green = Knowledge found, Yellow = Low confidence, Red = Error, Gray = No knowledge used. Confidence % shows source reliability.",
    docTab: "rag",
    docLabel: "Learn about RAG"
  },
  'citations': {
    title: "Citations",
    content: "Click citation numbers [1], [2] to view sources. Higher confidence % means more reliable information.",
    docTab: "rag",
    docLabel: "Citation Guide"
  },
  'knowledge-upload': {
    title: "Knowledge Upload",
    content: "Upload documents, connect repositories, or add knowledge entries to improve AI responses.",
    docTab: "knowledge",
    docLabel: "Knowledge Management"
  },
  'confidence-score': {
    title: "Confidence Score",
    content: "Shows how reliable the AI's sources are. 80%+ is high confidence, 60-80% is moderate, below 60% is low.",
    docTab: "rag",
    docLabel: "Understanding Confidence"
  },
  'effective-queries': {
    title: "Writing Good Queries",
    content: "Ask specific questions with context. Use structural syntax like 'function:name' for code searches.",
    docTab: "chat", 
    docLabel: "Query Examples"
  }
};

export const ContextualHelp = ({ 
  helpKey, 
  trigger, 
  tooltip, 
  position = 'top',
  onOpenDocumentation 
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);

  // Use provided tooltip content or lookup by key
  const tooltipData = tooltip || TOOLTIP_CONTENT[helpKey];
  
  if (!tooltipData) {
    console.warn(`Tooltip content not found for key: ${helpKey}`);
    return trigger || null;
  }

  const showTooltip = () => setIsVisible(true);
  const hideTooltip = () => setIsVisible(false);

  const handleOpenDocs = (e) => {
    e.stopPropagation();
    hideTooltip();
    if (onOpenDocumentation && tooltipData.docTab) {
      onOpenDocumentation(tooltipData.docTab);
    }
  };

  // Position tooltip to avoid viewport edges
  const getTooltipPosition = () => {
    if (!triggerRef.current) return {};
    
    const rect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = 280;
    const tooltipHeight = 80;
    
    let top, left;
    
    switch (position) {
      case 'top':
        top = rect.top - tooltipHeight - 8;
        left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        break;
      case 'bottom':
        top = rect.bottom + 8;
        left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        break;
      case 'left':
        top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
        left = rect.left - tooltipWidth - 8;
        break;
      case 'right':
        top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
        left = rect.right + 8;
        break;
      default:
        top = rect.top - tooltipHeight - 8;
        left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
    }
    
    // Adjust for viewport edges
    if (left < 8) left = 8;
    if (left + tooltipWidth > window.innerWidth - 8) {
      left = window.innerWidth - tooltipWidth - 8;
    }
    if (top < 8) top = rect.bottom + 8;
    
    return { top, left };
  };

  return (
    <div className="relative inline-block">
      {/* Trigger */}
      <div
        ref={triggerRef}
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
        className="inline-block"
      >
        {trigger || (
          <button className="text-gray-400 hover:text-gray-600 ml-1 transition-colors duration-200">
            <HelpCircle className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Tooltip */}
      {isVisible && (
        <>
          {/* Backdrop for mobile */}
          <div className="fixed inset-0 z-40 md:hidden" onClick={hideTooltip} />
          
          {/* Tooltip content */}
          <div
            ref={tooltipRef}
            className="fixed z-50 w-80 max-w-sm bg-gray-900 text-white text-sm rounded-lg shadow-lg pointer-events-auto"
            style={getTooltipPosition()}
          >
            <div className="p-3">
              {tooltipData.title && (
                <div className="font-medium mb-2 flex items-center gap-2">
                  <Info className="w-4 h-4 flex-shrink-0" />
                  {tooltipData.title}
                </div>
              )}
              <div className="text-gray-300 text-xs leading-relaxed mb-3">
                {typeof tooltipData === 'string' ? tooltipData : tooltipData.content}
              </div>
              
              {/* Documentation link */}
              {tooltipData.docTab && onOpenDocumentation && (
                <button
                  onClick={handleOpenDocs}
                  className="flex items-center gap-2 text-blue-400 hover:text-blue-300 text-xs font-medium transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  {tooltipData.docLabel || 'View Documentation'}
                </button>
              )}
            </div>
            
            {/* Arrow */}
            <div 
              className={`absolute w-2 h-2 bg-gray-900 transform rotate-45 ${
                position === 'top' ? 'bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2' :
                position === 'bottom' ? 'top-0 left-1/2 -translate-x-1/2 -translate-y-1/2' :
                position === 'left' ? 'right-0 top-1/2 -translate-y-1/2 translate-x-1/2' :
                'left-0 top-1/2 -translate-y-1/2 -translate-x-1/2'
              }`}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default ContextualHelp;