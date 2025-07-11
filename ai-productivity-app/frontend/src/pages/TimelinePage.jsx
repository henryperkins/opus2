/* TimelinePage.jsx – global activity log */

// React import intentionally omitted – not required with the new JSX transform
import { Link } from "react-router-dom";
import TimelineEvent from "../components/projects/TimelineEvent";
import { useTimeline } from "../hooks/useTimeline";

export default function TimelinePage() {
  const { events, loading, error } = useTimeline({ limit: 200 });

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8">
      <main className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Activity Log</h1>

        {loading && (
          <div className="flex items-center text-gray-500">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-2"></div>
            Loading timeline...
          </div>
        )}

        {error && <div className="text-red-600 mb-4">{error}</div>}

        {!loading && !events.length && (
          <div className="text-gray-400">No activity yet.</div>
        )}

        {!loading && events.length > 0 && (
          <div className="timeline border-l-2 pl-6">
            {events.map((evt) => (
              <div key={evt.id} className="mb-4">
                {/* Show project title with link */}
                <div className="mb-1 text-sm text-blue-600">
                  <Link to={`/projects/${evt.project_id}`}>
                    Project #{evt.project_id}
                  </Link>
                </div>
                <TimelineEvent event={evt} />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
