// Reusable status badge component
// Applies consistent gradient colours based on *status* prop.


/**
 * Badge – gradient pill displaying a status label.
 *
 * Props:
 *   • status   – "active" | "completed" | "archived" (string)
 *   • children – content inside the badge (usually label)
 */
export default function Badge({ status = 'active', children }) {
  const colourMap = {
    active:    'from-green-500 to-emerald-500',
    completed: 'from-blue-500 to-indigo-500',
    archived:  'from-gray-400 to-gray-500',
  };

  const gradient = colourMap[status] ?? 'from-gray-500 to-gray-700';

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium shadow-sm text-white bg-gradient-to-r ${gradient}`}
    >
      {children}
    </span>
  );
}
