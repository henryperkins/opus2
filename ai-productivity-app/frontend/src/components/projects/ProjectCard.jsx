// ProjectCard.jsx: visual card with status, emoji, tags, and quick actions.

import React from "react";

export default function ProjectCard({ project, onClick }) {
  return (
    <div
      className="project-card card card-hover p-6 flex flex-col cursor-pointer animate-scale-in"
      style={{
        borderLeft: project.color ? `6px solid ${project.color}` : undefined,
      }}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center text-2xl">
          {project.emoji && (
            <span className="mr-2" aria-label="emoji">
              {project.emoji}
            </span>
          )}
          <h2 className="font-semibold text-xl truncate">{project.title}</h2>
        </div>
        <span
          className={`inline-flex items-center px-3 py-1 rounded-full font-medium text-xs shadow-sm
            ${project.status === "active"
              ? "status-active"
              : project.status === "completed"
              ? "status-completed"
              : "status-archived"
            }
          `}
        >
          {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
        </span>
      </div>
      <div className="mt-2 text-gray-600 line-clamp-2">
        {project.description}
      </div>
      <div className="mt-3 flex flex-wrap gap-1">
        {(project.tags || []).map(tag => (
          <span
            key={tag}
            className="inline-flex items-center bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md px-2 py-1 text-xs font-medium transition-colors hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            #{tag}
          </span>
        ))}
      </div>
      <div className="flex-1" />
      <div className="flex justify-between items-center mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Last updated:{" "}
          {project.updated_at
            ? new Date(project.updated_at).toLocaleDateString()
            : "—"}
        </span>
        <div className="flex items-center space-x-1">
          <div className={`w-2 h-2 rounded-full ${
            project.status === 'active' ? 'bg-green-400' :
            project.status === 'completed' ? 'bg-blue-400' : 'bg-gray-400'
          }`} />
        </div>
      </div>
    </div>
  );
}
