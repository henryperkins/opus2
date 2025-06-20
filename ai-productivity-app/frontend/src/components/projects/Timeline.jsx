// Timeline.jsx: chronological timeline for project events.

import React, { useEffect, useState } from "react";
import useProjectStore from "../../stores/projectStore";
import TimelineEvent from "./TimelineEvent";
import { toast } from '../common/Toast';
import TimelineErrorBoundary from '../common/TimelineErrorBoundary';

export default function Timeline({ projectId }) {
  const { fetchTimeline, timeline, timelineLoading, timelineError, clearTimelineError } = useProjectStore();
  const [error, setError] = useState(null);
  const [filterType, setFilterType] = useState('all');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (projectId) {
      clearTimelineError(); // Clear previous errors
      fetchTimeline(projectId).catch(e => {
        setError(e.message);
        toast.error('Failed to load timeline');
      });
    }
    // eslint-disable-next-line
  }, [projectId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    clearTimelineError();
    try {
      await fetchTimeline(projectId);
      toast.success('Timeline refreshed');
    } catch (e) {
      setError(e.message);
      toast.error('Failed to refresh timeline');
    } finally {
      setRefreshing(false);
    }
  };

  const filteredTimeline = timeline.filter(event => {
    if (filterType === 'all') return true;
    if (filterType === 'canvas') return ['canvas_created', 'canvas_updated'].includes(event.event_type);
    if (filterType === 'chat') return ['chat_message', 'code_generated'].includes(event.event_type);
    if (filterType === 'system') return ['model_changed', 'dependency_analyzed', 'search_performed'].includes(event.event_type);
    return event.event_type === filterType;
  });

  if (timelineLoading) {
    return (
      <div className="space-y-4">
        {[1,2,3].map(i => (
          <div key={i} className="timeline-event relative mb-6 pl-8">
            <div className="absolute left-0 top-1 flex flex-col items-center">
              <div className="w-6 h-6 bg-gray-200 rounded-full animate-pulse"></div>
            </div>
            <div className="ml-2">
              <div className="flex items-center gap-2">
                <div className="h-4 bg-gray-200 rounded w-32 animate-pulse"></div>
                <div className="h-3 bg-gray-200 rounded w-16 animate-pulse"></div>
              </div>
              <div className="mt-1 h-3 bg-gray-200 rounded w-48 animate-pulse"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error || timelineError) {
    const displayError = error || timelineError;
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <svg className="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="text-sm font-medium text-red-800">Timeline Error</h3>
            <p className="text-sm text-red-600 mt-1">{displayError}</p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          className="mt-3 text-sm text-red-600 hover:text-red-800 underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!timeline.length) {
    return (
      <div className="text-center py-12">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No timeline events</h3>
        <p className="mt-1 text-sm text-gray-500">Start using the app to see activity here.</p>
      </div>
    );
  }

  return (
    <TimelineErrorBoundary onRetry={handleRefresh}>
      <div className="timeline-container">
        {/* Timeline Controls */}
        <div className="flex items-center justify-between mb-6 pb-3 border-b">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-medium text-gray-900">Activity Timeline</h3>
            <span className="text-sm text-gray-500">({filteredTimeline.length} events)</span>
          </div>
          
          <div className="flex items-center space-x-3">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="all">All Events</option>
              <option value="canvas">Canvas</option>
              <option value="chat">Chat & Code</option>
              <option value="system">System</option>
              <option value="file_added">Files</option>
            </select>
            
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
            >
              {refreshing ? (
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                'Refresh'
              )}
            </button>
          </div>
        </div>

        {/* Timeline Events */}
        <div className="timeline border-l-2 border-gray-200 pl-6">
          {filteredTimeline.map(event => (
            <TimelineEvent key={event.id} event={event} />
          ))}
        </div>
      </div>
    </TimelineErrorBoundary>
  );
}
