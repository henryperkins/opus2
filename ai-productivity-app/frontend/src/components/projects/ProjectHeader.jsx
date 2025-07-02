
export default function ProjectHeader({ project }) {
  if (!project) return null;

  return (
    <div className="project-info space-y-2">
      <h1 className="text-3xl font-bold">
        {project.emoji && <span className="mr-2">{project.emoji}</span>}
        {project.title}
      </h1>
      <p className="text-gray-600">{project.description}</p>

      <div className="flex items-center space-x-3">
        <span className={`badge-status-${project.status || 'active'}`}>
          {project.status || 'active'}
        </span>
        <span className="text-xs text-gray-500">
          Created {new Date(project.created_at).toLocaleDateString()} ·
          Updated {new Date(project.updated_at).toLocaleDateString()}
        </span>
        {project.tags?.map(t => (
          <span key={t} className="tag">{t}</span>
        ))}
      </div>
    </div>
  );
}