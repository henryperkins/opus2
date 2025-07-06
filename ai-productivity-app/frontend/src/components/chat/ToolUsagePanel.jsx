import React, { useState, useEffect } from 'react';
import { 
  Wrench, 
  Search, 
  Code, 
  FileText, 
  GitBranch, 
  TestTube, 
  ExternalLink, 
  Brain,
  Settings,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Play,
  Pause
} from 'lucide-react';

const AVAILABLE_TOOLS = [
  {
    id: 'file_search',
    name: 'Code Search',
    description: 'Search for code patterns and implementations',
    icon: Search,
    category: 'code',
    color: 'blue'
  },
  {
    id: 'explain_code',
    name: 'Code Explanation',
    description: 'Explain specific code functionality',
    icon: Code,
    category: 'code',
    color: 'green'
  },
  {
    id: 'generate_tests',
    name: 'Test Generation',
    description: 'Generate unit tests for functions',
    icon: TestTube,
    category: 'code',
    color: 'purple'
  },
  {
    id: 'similar_code',
    name: 'Similar Code',
    description: 'Find semantically similar code',
    icon: GitBranch,
    category: 'code',
    color: 'orange'
  },
  {
    id: 'search_commits',
    name: 'Commit Search',
    description: 'Search git commit history',
    icon: GitBranch,
    category: 'git',
    color: 'indigo'
  },
  {
    id: 'git_blame',
    name: 'Git Blame',
    description: 'Get blame information for files',
    icon: FileText,
    category: 'git',
    color: 'gray'
  },
  {
    id: 'analyze_code_quality',
    name: 'Code Quality',
    description: 'Run static analysis on code',
    icon: Settings,
    category: 'analysis',
    color: 'red'
  },
  {
    id: 'fetch_documentation',
    name: 'Documentation Fetcher',
    description: 'Fetch and analyze external docs',
    icon: ExternalLink,
    category: 'research',
    color: 'blue'
  },
  {
    id: 'comprehensive_analysis',
    name: 'Deep Analysis',
    description: 'Structured thinking and analysis',
    icon: Brain,
    category: 'analysis',
    color: 'purple'
  }
];

const TOOL_CATEGORIES = [
  { id: 'code', name: 'Code Tools', color: 'blue' },
  { id: 'git', name: 'Git Tools', color: 'green' },
  { id: 'analysis', name: 'Analysis Tools', color: 'purple' },
  { id: 'research', name: 'Research Tools', color: 'orange' }
];

export default function ToolUsagePanel({ 
  enabledTools = [], 
  onToolToggle, 
  recentToolCalls = [],
  onRunTool,
  compact = false 
}) {
  const [expandedCategories, setExpandedCategories] = useState({
    code: true,
    git: false,
    analysis: true,
    research: true
  });
  const [showRecentCalls, setShowRecentCalls] = useState(false);

  const toggleCategory = (categoryId) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryId]: !prev[categoryId]
    }));
  };

  const isToolEnabled = (toolId) => {
    return enabledTools.includes(toolId);
  };

  const getToolsByCategory = (categoryId) => {
    return AVAILABLE_TOOLS.filter(tool => tool.category === categoryId);
  };

  const getRecentCallsForTool = (toolId) => {
    return recentToolCalls.filter(call => call.toolId === toolId);
  };

  const formatCallDuration = (duration) => {
    if (duration < 1000) return `${duration}ms`;
    return `${(duration / 1000).toFixed(1)}s`;
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  if (compact) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-gray-600" />
            <span className="font-medium text-sm">Tools</span>
          </div>
          <span className="text-xs text-gray-500">
            {enabledTools.length} enabled
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {AVAILABLE_TOOLS.map(tool => {
            const IconComponent = tool.icon;
            const enabled = isToolEnabled(tool.id);
            
            return (
              <button
                key={tool.id}
                onClick={() => onToolToggle?.(tool.id, !enabled)}
                className={`flex items-center gap-2 p-2 rounded border transition-colors ${
                  enabled 
                    ? `border-${tool.color}-300 bg-${tool.color}-50 text-${tool.color}-700`
                    : 'border-gray-200 bg-gray-50 text-gray-500 hover:bg-gray-100'
                }`}
              >
                <IconComponent className="h-3 w-3" />
                <span className="text-xs font-medium truncate">{tool.name}</span>
              </button>
            );
          })}
        </div>

        {recentToolCalls.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="text-xs font-medium text-gray-600 mb-2">Recent Calls</div>
            <div className="space-y-1">
              {recentToolCalls.slice(0, 3).map((call, index) => (
                <div key={index} className="flex items-center justify-between text-xs">
                  <span className="text-gray-600 truncate">{call.toolName}</span>
                  <div className="flex items-center gap-1">
                    {getStatusIcon(call.status)}
                    <span className="text-gray-500">{formatCallDuration(call.duration)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="h-5 w-5 text-gray-700" />
          <h3 className="font-semibold text-gray-900">Tool Usage</h3>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>{enabledTools.length} of {AVAILABLE_TOOLS.length} enabled</span>
        </div>
      </div>

      {/* Tool Categories */}
      <div className="space-y-3">
        {TOOL_CATEGORIES.map(category => {
          const categoryTools = getToolsByCategory(category.id);
          const isExpanded = expandedCategories[category.id];
          const enabledInCategory = categoryTools.filter(tool => isToolEnabled(tool.id)).length;
          
          return (
            <div key={category.id} className="border border-gray-200 rounded-lg">
              <button
                onClick={() => toggleCategory(category.id)}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-500" />
                  )}
                  <span className="font-medium text-gray-900">{category.name}</span>
                  <span className={`px-2 py-1 text-xs rounded bg-${category.color}-100 text-${category.color}-700`}>
                    {enabledInCategory}/{categoryTools.length}
                  </span>
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-gray-200 p-3 space-y-2">
                  {categoryTools.map(tool => {
                    const IconComponent = tool.icon;
                    const enabled = isToolEnabled(tool.id);
                    const recentCalls = getRecentCallsForTool(tool.id);
                    
                    return (
                      <div
                        key={tool.id}
                        className={`p-3 border rounded-lg transition-colors ${
                          enabled 
                            ? `border-${tool.color}-300 bg-${tool.color}-50`
                            : 'border-gray-200 bg-white hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded ${
                              enabled 
                                ? `bg-${tool.color}-100`
                                : 'bg-gray-100'
                            }`}>
                              <IconComponent className={`h-4 w-4 ${
                                enabled 
                                  ? `text-${tool.color}-600`
                                  : 'text-gray-500'
                              }`} />
                            </div>
                            <div>
                              <div className={`font-medium ${
                                enabled ? `text-${tool.color}-900` : 'text-gray-700'
                              }`}>
                                {tool.name}
                              </div>
                              <div className="text-sm text-gray-500">{tool.description}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {enabled && onRunTool && (
                              <button
                                onClick={() => onRunTool(tool.id)}
                                className={`p-1 rounded hover:bg-${tool.color}-200 text-${tool.color}-600`}
                              >
                                <Play className="h-4 w-4" />
                              </button>
                            )}
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input
                                type="checkbox"
                                checked={enabled}
                                onChange={(e) => onToolToggle?.(tool.id, e.target.checked)}
                                className="sr-only peer"
                              />
                              <div className={`w-8 h-4 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-${tool.color}-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-${tool.color}-600`}></div>
                            </label>
                          </div>
                        </div>

                        {/* Recent calls for this tool */}
                        {enabled && recentCalls.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="text-xs font-medium text-gray-600 mb-2">
                              Recent Calls ({recentCalls.length})
                            </div>
                            <div className="space-y-1">
                              {recentCalls.slice(0, 2).map((call, index) => (
                                <div key={index} className="flex items-center justify-between text-xs">
                                  <span className="text-gray-600 truncate">{call.description}</span>
                                  <div className="flex items-center gap-2">
                                    {getStatusIcon(call.status)}
                                    <span className="text-gray-500">{formatCallDuration(call.duration)}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Recent Tool Calls */}
      {recentToolCalls.length > 0 && (
        <div className="border border-gray-200 rounded-lg">
          <button
            onClick={() => setShowRecentCalls(!showRecentCalls)}
            className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              {showRecentCalls ? (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" />
              )}
              <span className="font-medium text-gray-900">Recent Tool Calls</span>
              <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-700">
                {recentToolCalls.length}
              </span>
            </div>
          </button>

          {showRecentCalls && (
            <div className="border-t border-gray-200 p-3">
              <div className="space-y-2">
                {recentToolCalls.map((call, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(call.status)}
                      <span className="font-medium text-sm">{call.toolName}</span>
                      <span className="text-sm text-gray-500">{call.description}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span>{formatCallDuration(call.duration)}</span>
                      <span>{new Date(call.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}