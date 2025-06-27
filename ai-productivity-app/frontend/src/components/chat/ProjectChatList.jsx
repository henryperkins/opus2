import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import { format } from 'date-fns';
import chatAPI from '../../api/chat';
import LoadingSpinner from '../common/LoadingSpinner';
import EmptyState from '../common/EmptyState';
import { MessageSquare, Plus, Clock, ChevronRight } from 'lucide-react';

export default function ProjectChatList({ projectId, project }) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);

  // Load chat sessions for this project
  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await chatAPI.getChatSessions({ project_id: projectId });
      const sessionsData = response?.data || response;
      setSessions(Array.isArray(sessionsData) ? sessionsData : sessionsData.items || []);
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
      setError('Failed to load chat sessions');
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    try {
      setCreating(true);
      const response = await chatAPI.createSession({ 
        project_id: Number(projectId),
        title: `Chat - ${new Date().toLocaleDateString()}`
      });
      const newSession = response.data;
      navigate(`/projects/${projectId}/chat/${newSession.id}`);
    } catch (err) {
      console.error('Failed to create chat session:', err);
      setError('Failed to create new chat');
    } finally {
      setCreating(false);
    }
  };

  const openChat = (sessionId) => {
    navigate(`/projects/${projectId}/chat/${sessionId}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Project Chats
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Continue a conversation or start a new one
          </p>
        </div>
        <button
          onClick={createNewChat}
          disabled={creating}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Plus className="w-4 h-4" />
          {creating ? 'Creating...' : 'New Chat'}
        </button>
      </div>

      {/* Chat Sessions List */}
      {sessions.length === 0 ? (
        <EmptyState
          icon={MessageSquare}
          title="No chats yet"
          description="Start a new chat to begin collaborating with AI on this project"
          action={{
            label: 'Start First Chat',
            onClick: createNewChat
          }}
        />
      ) : (
        <div className="grid gap-3">
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => openChat(session.id)}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-blue-500 dark:hover:border-blue-400 cursor-pointer transition-all group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-gray-400" />
                    <h3 className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                      {session.title || `Chat Session #${session.id}`}
                    </h3>
                  </div>
                  
                  {session.summary && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                      {session.summary}
                    </p>
                  )}

                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-500">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {format(new Date(session.updated_at), 'MMM d, h:mm a')}
                    </div>
                    {session.message_count > 0 && (
                      <div className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" />
                        {session.message_count} messages
                      </div>
                    )}
                    {session.is_active && (
                      <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-xs">
                        Active
                      </span>
                    )}
                  </div>
                </div>
                
                <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

ProjectChatList.propTypes = {
  projectId: PropTypes.string.isRequired,
  project: PropTypes.object // Optional project object for additional metadata
};