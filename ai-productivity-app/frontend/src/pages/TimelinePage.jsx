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
        {/* Breadcrumb */}
        <nav className="flex mb-4 text-sm" aria-label="Breadcrumb">
          <ol className="inline-flex items-center space-x-1 md:space-x-2 rtl:space-x-reverse">
            <li className="inline-flex items-center">
              <Link
                to="/"
                className="inline-flex items-center text-gray-500 hover:text-gray-300 dark:hover:text-gray-300"
              >
                <svg
                  className="w-4 h-4 mr-1"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M10 2a1 1 0 01.707.293l7 7-1.414 1.414L10 4.414 3.707 10.707 2.293 9.293l7-7A1 1 0 0110 2z" />
                  <path d="M3 10l7 7 7-7" />
                </svg>
                Dashboard
              </Link>
            </li>
            <li>
              <div className="flex items-center">
                <svg
                  className="w-4 h-4 text-gray-400 dark:text-gray-500 mx-1"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M7.05 4.05a7 7 0 019.9 9.9l-6.364 6.364a.75.75 0 01-1.06 0L2.343 14.05a7 7 0 014.707-9.999Z" />
                </svg>
                <span className="ml-1 text-gray-700 dark:text-gray-300 font-medium">Timeline</span>
              </div>
            </li>
          </ol>
        </nav>

        <h1 className="text-3xl font-bold text-gray-900 mb-6">Activity Log</h1>

        {loading && (
          <div className="flex items-center text-gray-500">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-2"></div>
            Loading timeline...
          </div>
        )}

        {error && (
          <div className="text-red-600 mb-4">{error}</div>
        )}

        {!loading && !events.length && (
          <div className="text-gray-400">No activity yet.</div>
        )}

        {!loading && events.length > 0 && (
          <div className="timeline border-l-2 pl-6">
            {events.map((evt) => (
              <div key={evt.id} className="mb-4">
                {/* Show project title with link */}
                <div className="mb-1 text-sm text-blue-600">
                  <Link to={`/projects/${evt.project_id}`}>Project #{evt.project_id}</Link>
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
