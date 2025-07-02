import { MessageCircle, FileText, BarChart2, BookOpen, Search } from 'lucide-react';
import { Link } from 'react-router-dom';

const items = [
  { to: 'chat', icon: MessageCircle, label: 'Chat' },
  { to: 'files', icon: FileText, label: 'Files' },
  { to: 'analytics', icon: BarChart2, label: 'Analytics' },
  { to: 'knowledge', icon: BookOpen, label: 'Knowledge' },
  { to: '../../search', icon: Search, label: 'Search', absolute: true }
];

export default function QuickActions({ projectId }) {
  return (
    <section className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
      {items.map(({ to, icon: Icon, label, absolute }) => (
        <Link 
          key={label}
          to={absolute ? `${to}?projectIds[]=${projectId}` : to}
          className="action-card"
        >
          <Icon className="w-5 h-5 mr-2" /> 
          {label}
        </Link>
      ))}
    </section>
  );
}