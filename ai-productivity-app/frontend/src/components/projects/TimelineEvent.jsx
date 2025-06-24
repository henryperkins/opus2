// TimelineEvent.jsx: an individual project event.

import React from "react";

function eventIcon(type) {
  switch (type) {
    case "created":
      return "🟢";
    case "updated":
      return "✏️";
    case "archived":
      return "📦";
    case "file_added":
      return "📄";
    case "canvas_created":
      return "🎨";
    case "canvas_updated":
      return "🖌️";
    case "chat_message":
      return "💬";
    case "code_generated":
      return "⚡";
    case "model_changed":
      return "🤖";
    case "dependency_analyzed":
      return "🔗";
    case "search_performed":
      return "🔍";
    default:
      return "⏺️";
  }
}

function formatRelative(ts) {
  const date = typeof ts === "string" ? new Date(ts) : ts;
  const now = Date.now();
  const diffMins = Math.floor((now - date) / 60000);
  if (diffMins < 60) return `${diffMins || 1}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function TimelineEvent({ event }) {
  const renderEventDetails = () => {
    const { metadata } = event;
    
    if (!metadata) return null;

    switch (event.event_type) {
      case "canvas_created":
      case "canvas_updated":
        return (
          <div className="mt-2 p-2 bg-purple-50 rounded text-xs">
            <div className="flex items-center justify-between">
              <span className="font-medium">Canvas: {metadata.canvas_name}</span>
              {metadata.shapes_count && (
                <span className="text-purple-600">{metadata.shapes_count} elements</span>
              )}
            </div>
          </div>
        );
      
      case "chat_message":
        return metadata.message_type === 'command' ? (
          <div className="mt-2 p-2 bg-blue-50 rounded text-xs">
            <span className="font-mono text-blue-700">{metadata.command}</span>
          </div>
        ) : null;
      
      case "code_generated":
        return (
          <div className="mt-2 p-2 bg-green-50 rounded text-xs">
            <div className="flex items-center justify-between">
              <span className="font-medium">{metadata.language} code</span>
              {metadata.lines_count && (
                <span className="text-green-600">{metadata.lines_count} lines</span>
              )}
            </div>
          </div>
        );
      
      case "model_changed":
        return (
          <div className="mt-2 p-2 bg-orange-50 rounded text-xs">
            <div className="flex items-center justify-between">
              <span>From: <span className="font-mono">{metadata.old_model}</span></span>
              <span>To: <span className="font-mono">{metadata.new_model}</span></span>
            </div>
          </div>
        );
      
      case "search_performed":
        return (
          <div className="mt-2 p-2 bg-yellow-50 rounded text-xs">
            <div className="flex items-center justify-between">
              <span className="font-medium">Query: "{metadata.query}"</span>
              {metadata.results_count && (
                <span className="text-yellow-700">{metadata.results_count} results</span>
              )}
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="timeline-event relative mb-6 pl-8">
      <div className="absolute left-0 top-1 flex flex-col items-center">
        <span className="text-lg">{eventIcon(event.event_type)}</span>
        <span className="w-1 h-full bg-gray-300 dark:bg-gray-700 absolute top-6" />
      </div>
      <div className="ml-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{event.title}</span>
          <span className="text-gray-400 dark:text-gray-500 text-xs">{formatRelative(event.created_at)}</span>
        </div>
        {event.description && (
          <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">{event.description}</div>
        )}
        {renderEventDetails()}
      </div>
    </div>
  );
}
