// ProjectFilters.jsx: Status, tag, searchbox, and reset controls.

import React from "react";

const STATUS_OPTIONS = [
  { label: "All", value: null },
  { label: "Active", value: "active" },
  { label: "Archived", value: "archived" },
  { label: "Completed", value: "completed" },
];

export default function ProjectFilters({ filters, onChange }) {
  const handleStatus = (e) => {
    onChange({ ...filters, status: e.target.value || null });
  };
  const handleSearch = (e) => {
    onChange({ ...filters, search: e.target.value });
  };
  const handleTags = (e) => {
    const tags = e.target.value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    onChange({ ...filters, tags });
  };
  const handleReset = () => {
    onChange({ status: null, tags: [], search: "", page: 1 });
  };

  return (
    <form
      className="flex flex-wrap gap-4 items-end mb-8"
      onSubmit={(e) => e.preventDefault()}
    >
      <div>
        <label className="block font-medium mb-1">Status</label>
        <select
          value={filters.status || ""}
          onChange={handleStatus}
          className="form-select"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.label} value={opt.value || ""}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block font-medium mb-1">Tags</label>
        <input
          type="text"
          value={(filters.tags || []).join(", ")}
          onChange={handleTags}
          placeholder="Comma separated"
          className="form-input"
        />
      </div>

      <div className="flex-1">
        <label className="block font-medium mb-1">Search</label>
        <input
          type="text"
          value={filters.search || ""}
          onChange={handleSearch}
          placeholder="Project title, description, tags…"
          className="form-input w-full"
        />
      </div>

      <button
        type="button"
        className="btn btn-secondary ml-2"
        onClick={handleReset}
      >
        Reset
      </button>
    </form>
  );
}
