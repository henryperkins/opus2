// ProjectCard.jsx: visual card with status, emoji, tags, and quick actions.

import React from "react";

export default function ProjectCard({ project }) {
  return (
    <div
      className="project-card border border-gray-100 p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow flex flex-col"
      style={{
        borderLeft: project.color ? `8px solid ${project.color}` : undefined,
      }}
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
          className={`inline-flex items-center px-3 py-1 rounded-full font-semibold text-xs
            ${project.status === "active"
              ? "bg-green-100 text-green-800"
              : project.status === "completed"
              ? "bg-blue-100 text-blue-800"
              : "bg-gray-100 text-gray-800"
            }
          `}
        >
          {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
        </span>
      </div>
      <div className="mt-2 text-gray-600 line-clamp-2">
        {project.description}
      </div>
      <div className="mt-3">
        {(project.tags || []).map(tag => (
          <span
            key={tag}
            className="inline-block bg-gray-200 text-gray-700 rounded px-2 py-0.5 mr-1 text-xs"
          >
            #{tag}
          </span>
        ))}
      </div>
      <div className="flex-1" />
      <div className="flex justify-between items-center mt-4 text-xs text-gray-400">
        <span>
          Last updated:{" "}
          {project.updated_at
            ? new Date(project.updated_at).toLocaleDateString()
            : "—"}
        </span>
        {/* Quick actions: props for onEdit, onArchive, onDelete would go here */}
        {/* <button .../> */}
      </div>
    </div>
  );
}
