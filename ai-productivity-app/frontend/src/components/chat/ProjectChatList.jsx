import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import PropTypes from 'prop-types';
import { format } from 'date-fns';
import chatAPI from '../../api/chat';
import LoadingSpinner from '../common/LoadingSpinner';
import EmptyState from '../common/EmptyState';
import { MessageSquare, Plus, Clock, ChevronRight, Pencil, Trash2, Check, X } from 'lucide-react';

export default function ProjectChatList({ projectId, project }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const LIMIT = 20;                  // page size – keep in sync with backend default
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);           // zero-based page index
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState(null);   // id being renamed
  const [newTitle, setNewTitle] = useState('');
  const [busyId, setBusyId] = useState(null);   // spinner for save/del

  // Load first page whenever project changes
  useEffect(() => {
    setSessions([]);
    setPage(0);
    setHasMore(true);
    loadSessions(0, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const loadSessions = async (pageIndex = 0, reset = false) => {
    if (reset) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }

    try {
      setError(null);
      const response = await chatAPI.getChatSessions({
        project_id: projectId,
        limit: LIMIT,
        offset: pageIndex * LIMIT,
      });

      const raw = response?.data || response;
      const items = Array.isArray(raw) ? raw : raw.items || [];

      setSessions((prev) => (reset ? items : [...prev, ...items]));

      // Determine if more pages remain
      if (
        items.length < LIMIT ||
        (!Array.isArray(raw) &&
          raw.total !== undefined &&
          (pageIndex + 1) * LIMIT >= raw.total)
      ) {
        setHasMore(false);
      }

      setPage(pageIndex + 1);
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
      setError('Failed to load chat sessions');
      setHasMore(false);
    } finally {
      if (reset) {
        setLoading(false);
      } else {
        setLoadingMore(false);
      }
    }
  };

  const loadMoreSessions = () => {
    if (hasMore && !loadingMore) {
      loadSessions(page);
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

  // Persist new title
  const saveTitle = async () => {
    if (!newTitle.trim()) return;
    try {
      setBusyId(editingId);
      await chatAPI.updateSession(editingId, { title: newTitle.trim() });
      setSessions(s => s.map(sess =>
        sess.id === editingId ? { ...sess, title: newTitle.trim() } : sess));

      // Invalidate sidebar recent chats cache to update titles immediately
      queryClient.invalidateQueries(['recentChats']);
    } catch (err) {
      setError('Failed to rename chat session');
    } finally {
      setBusyId(null);
      setEditingId(null);
    }
  };

  // Ask & delete
  const confirmDelete = (id) => {
    if (!window.confirm('Delete this conversation?')) return;
    deleteSession(id);
  };

  const deleteSession = async (id) => {
    try {
      setBusyId(id);
      await chatAPI.deleteSession(id);
      setSessions(s => s.filter(sess => sess.id !== id));
    } catch (err) {
      setError('Failed to delete chat session');
    } finally {
      setBusyId(null);
    }
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

                {/* actions / chevron */}
                <div
                  className="flex items-center gap-1 text-gray-400 group-hover:text-gray-600
                             dark:text-gray-500 dark:group-hover:text-gray-300"
                  onClick={(e) => e.stopPropagation()}   /* keep card from navigating */
                >
                  {editingId === session.id ? (
                    <>
                      <input
                        value={newTitle}
                        onChange={e => setNewTitle(e.target.value)}
                        className="w-40 px-1 py-0.5 text-sm rounded border
                                   dark:bg-gray-700 dark:border-gray-600"
                      />
                      <Check
                        className={`w-4 h-4 cursor-pointer ${busyId===session.id&&'animate-spin'}`}
                        aria-label="Save"
                        onClick={saveTitle}
                      />
                      <X
                        className="w-4 h-4 cursor-pointer"
                        aria-label="Cancel"
                        onClick={() => setEditingId(null)}
                      />
                    </>
                  ) : (
                    <>
                      <Pencil
                        className="w-4 h-4 cursor-pointer"
                        aria-label="Edit title"
                        onClick={() => { setEditingId(session.id); setNewTitle(session.title || ''); }}
                      />
                      <Trash2
                        className={`w-4 h-4 cursor-pointer ${busyId===session.id&&'animate-spin'}`}
                        aria-label="Delete conversation"
                        onClick={() => confirmDelete(session.id)}
                      />
                      <ChevronRight className="w-5 h-5" />
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
          {hasMore && (
            <button
              onClick={loadMoreSessions}
              disabled={loadingMore}
              className="px-4 py-2 mx-auto my-2 text-sm text-blue-600 dark:text-blue-400 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loadingMore ? 'Loading…' : 'Load More'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

ProjectChatList.propTypes = {
  projectId: PropTypes.string.isRequired,
  project: PropTypes.object // Optional project object for additional metadata
};
