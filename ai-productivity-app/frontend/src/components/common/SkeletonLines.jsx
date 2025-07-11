/**
 * SkeletonLines – animated placeholder rows.
 * @param {number} rows  Number of grey bars to render (default 6)
 */
export default function SkeletonLines({ rows = 6, className = "" }) {
  return (
    <div className={`space-y-2 ${className}`} data-testid="skeleton-lines">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          // eslint-disable-next-line react/no-array-index-key
          key={i}
          className="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"
        />
      ))}
    </div>
  );
}
