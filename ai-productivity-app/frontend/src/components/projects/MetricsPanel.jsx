
export default function MetricsPanel({ quality, kb }) {
  if (!quality && !kb) return null;

  const stats = {
    ...(quality || {}),
    knowledge_entries: kb?.entry_count
  };

  return (
    <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {Object.entries(stats)
        .filter(
          ([, v]) =>
            v != null && (typeof v === 'number' || typeof v === 'string')
        )
        .map(([k, v]) => (
        <div key={k} className="card p-4">
          <dt className="text-sm text-gray-500 capitalize">
            {k.replace(/_/g, ' ')}
          </dt>
          <dd className="text-2xl font-semibold">
            {typeof v === 'number' ? v.toLocaleString() : v}
          </dd>
        </div>
      ))}
    </section>
  );
}
