import React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export default function Section({ title, icon: Icon, expanded, onToggle, children }) {
  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 rounded-t-lg"
      >
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-medium text-gray-800">{title}</h3>
        </div>
        {expanded ? (
          <ChevronDown className="h-5 w-5 text-gray-500" />
        ) : (
          <ChevronRight className="h-5 w-5 text-gray-500" />
        )}
      </button>
      {expanded && <div className="p-4 bg-white rounded-b-lg">{children}</div>}
    </div>
  );
}
