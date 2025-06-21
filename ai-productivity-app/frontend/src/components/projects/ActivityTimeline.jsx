import React from 'react';
import Timeline from './Timeline';

export default function ActivityTimeline({ projectId }) {
  return (
    <section>
      <h2 className="text-lg font-medium mb-4">Recent Activity</h2>
      <Timeline projectId={projectId} limit={10} compact />
    </section>
  );
}