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
  return (
    <div className="timeline-event relative mb-6 pl-8">
      <div className="absolute left-0 top-1 flex flex-col items-center">
        <span className="text-lg">{eventIcon(event.event_type)}</span>
        <span className="w-1 h-full bg-gray-300 absolute top-6" />
      </div>
      <div className="ml-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{event.title}</span>
          <span className="text-gray-400 text-xs">{formatRelative(event.created_at)}</span>
        </div>
        {event.description && (
          <div className="mt-1 text-sm text-gray-600">{event.description}</div>
        )}
      </div>
    </div>
  );
}
