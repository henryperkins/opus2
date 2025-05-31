// Timeline.jsx: chronological timeline for project events.

import React, { useEffect, useState } from "react";
import { useProjectStore } from "../../stores/projectStore";
import TimelineEvent from "./TimelineEvent";

export default function Timeline({ projectId }) {
  const { fetchTimeline, timeline, loading } = useProjectStore();
  const [error, setError] = useState(null);

  useEffect(() => {
    if (projectId) {
      fetchTimeline(projectId).catch(e => setError(e.message));
    }
    // eslint-disable-next-line
  }, [projectId]);

  if (loading) return <div>Loading timeline...</div>;
  if (error) return <div className="text-red-600">{error}</div>;
  if (!timeline.length) return <div className="text-gray-400">No events yet.</div>;

  return (
    <div className="timeline border-l-2 pl-6">
      {timeline.map(event => (
        <TimelineEvent key={event.id} event={event} />
      ))}
    </div>
  );
}
