import React from 'react';
import PropTypes from 'prop-types';
import { Search, MessageCircle, FileText, Brain, Plus } from 'lucide-react';

/**
 * Contextual empty state component with helpful user guidance
 * Displays appropriate empty states for different scenarios
 */
export default function EmptyState({
  type = 'default',
  title,
  description,
  action,
  icon: CustomIcon,
  className = ''
}) {
  const getDefaultContent = () => {
    switch (type) {
      case 'search':
        return {
          icon: Search,
          title: 'No results found',
          description: 'Try adjusting your search terms or check your spelling.',
          action: { text: 'Clear search', variant: 'secondary' }
        };

      case 'chat':
        return {
          icon: MessageCircle,
          title: 'Start a conversation',
          description: 'Ask a question about your code or request help with your project.',
          action: { text: 'Ask a question', variant: 'primary' }
        };

      case 'knowledge':
        return {
          icon: FileText,
          title: 'No knowledge context',
          description: 'Upload files or connect a repository to get AI assistance with your code.',
          action: { text: 'Upload files', variant: 'primary' }
        };

      case 'ai-suggestions':
        return {
          icon: Brain,
          title: 'No AI suggestions available',
          description: 'Select some code or ask a specific question to get AI-powered recommendations.',
          action: { text: 'Select code', variant: 'secondary' }
        };

      case 'projects':
        return {
          icon: Plus,
          title: 'No projects yet',
          description: 'Create your first project to start getting AI assistance with your code.',
          action: { text: 'Create project', variant: 'primary' }
        };

      default:
        return {
          icon: FileText,
          title: 'Nothing here yet',
          description: 'Content will appear here when available.',
          action: null
        };
    }
  };

  const defaults = getDefaultContent();
  const Icon = CustomIcon || defaults.icon;
  const finalTitle = title || defaults.title;
  const finalDescription = description || defaults.description;
  const finalAction = action || defaults.action;

  return (
    <div className={`flex flex-col items-center justify-center text-center py-12 px-6 ${className}`}>
      <div className="w-16 h-16 text-gray-400 mb-4">
        <Icon className="w-full h-full" />
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {finalTitle}
      </h3>

      <p className="text-gray-600 mb-6 max-w-md">
        {finalDescription}
      </p>

      {finalAction && (
        <button
          onClick={finalAction.onClick}
          className={`font-medium py-2 px-4 rounded-lg transition-colors ${
            finalAction.variant === 'primary'
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-gray-200 hover:bg-gray-300 text-gray-800'
          }`}
        >
          {finalAction.text}
        </button>
      )}
    </div>
  );
}

EmptyState.propTypes = {
  type: PropTypes.oneOf([
    'default',
    'search',
    'chat',
    'knowledge',
    'ai-suggestions',
    'projects'
  ]),
  title: PropTypes.string,
  description: PropTypes.string,
  action: PropTypes.shape({
    text: PropTypes.string.isRequired,
    onClick: PropTypes.func,
    variant: PropTypes.oneOf(['primary', 'secondary'])
  }),
  icon: PropTypes.elementType,
  className: PropTypes.string
};
