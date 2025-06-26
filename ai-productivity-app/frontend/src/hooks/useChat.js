// useChat.js – Chat WebSocket + React-Query powered hook
//-------------------------------------------------------
// Replaces the earlier monolithic stateful version with:
//   • React-Query cache for historical messages
//   • useWebSocketChannel for live streaming / updates
//   • Optimistic mutations for edit / delete

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import chatAPI from '../api/chat';
import { useAuth } from './useAuth';
import { useWebSocketChannel } from './useWebSocketChannel';
// import { useConfig } from './useConfig'; // Temporarily disabled - not used

// -----------------------
// Helpers & keys
// -----------------------
const messagesKey = (sessionId) => ['messages', sessionId];

// -----------------------
// Hook
// -----------------------
export function useChat(projectId, preferredSessionId = null) {
  const { user, loading: authLoading } = useAuth();
  // const { config } = useConfig(); // Temporarily disabled - not used
  const qc = useQueryClient();

  const [typingUsers, setTypingUsers] = useState(new Set());
  const [streamingMessages, setStreamingMessages] = useState(new Map());

  // ---------------------------------------------------
  // 1. Session bootstrap (React Query-driven approach)
  // ---------------------------------------------------
  const { data: sessionData, isLoading: sessionLoading } = useQuery({
    // Include *both* projectId **and** preferredSessionId in the React-Query
    // key so navigating between different chat sessions inside the same
    // project triggers a fresh query & cache entry.  This fixes the sidebar
    // navigation issue where the view did not update after selecting another
    // chat session.
    queryKey: ['session', projectId, preferredSessionId || 'default'],
    queryFn: async () => {
      if (!projectId || authLoading || !user) return null;

      // Prefer the session explicitly requested via the URL.  If none is
      // provided, fall back to a previously cached session for this project.
      const cached = qc.getQueryData(['session', projectId, preferredSessionId || 'default'])?.id;
      let sid = preferredSessionId ?? cached;

      try {
        // First try to validate the preferred or cached session
        if (sid) {
          const { data } = await chatAPI.getSession(sid);
          if (data.project_id === Number(projectId)) {
            return { id: sid, ...data };
          }
        }

        // Create new session if needed
        const { data } = await chatAPI.createSession({
          project_id: Number(projectId),
        });
        return data;
      } catch (error) {
        console.error('Session bootstrap error:', error);
        throw error;
      }
    },
    enabled: !!projectId && !authLoading && !!user,
    staleTime: Infinity,
    cacheTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const sessionId = sessionData?.id;

  // ---------------------------------------------------
  // 2. Historical messages (depends on session)
  // ---------------------------------------------------
  const {
    data: messages = [],
    isFetching: historyLoading,
  } = useQuery({
    queryKey: messagesKey(sessionId),
    queryFn: () => chatAPI.getMessages(sessionId).then((r) => r.data),
    enabled: !!sessionId && !sessionLoading,
    staleTime: 30 * 1000, // 30 seconds - messages can change frequently
  });

  // ---------------------------------------------------
  // 3. Live WebSocket connection (managed by query key)
  // ---------------------------------------------------
  const { state: connectionState, send } = useWebSocketChannel({
    path: sessionId ? `/api/chat/ws/sessions/${sessionId}` : null,
    retry: 3, // Limit to 3 attempts with exponential backoff
    onMessage: useCallback((event) => {
      try {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case 'message':
            qc.setQueryData(messagesKey(sessionId), (prev = []) => [...prev, data.message]);
            break;
          case 'typing':
            setTypingUsers((prev) => {
              const next = new Set(prev);
              data.typing ? next.add(data.user_id) : next.delete(data.user_id);
              return next;
            });
            break;
          case 'ai_stream': {
            // New backend streaming format: sends partial chunks until done=true
            if (!data.done) {
              // Handle in-flight chunk
              setStreamingMessages((prev) => {
                const map = new Map(prev);
                const m = map.get(data.message_id) || { id: data.message_id, content: '', isStreaming: true };
                // Create new object to avoid mutation
                const updatedMessage = {
                  ...m,
                  content: m.content + (data.content || ''),
                  lastUpdated: Date.now()
                };
                map.set(data.message_id, updatedMessage);
                return map;
              });
            } else {
              // Stream finished, commit final assistant message
              setStreamingMessages((prev) => {
                const map = new Map(prev);
                const streamingMessage = map.get(data.message_id);

                if (streamingMessage) {
                  const finalContent = streamingMessage.content || data.content || '';

                  const completeMessage = data.message || {
                    id: data.message_id,
                    role: 'assistant',
                    content: finalContent,
                    created_at: new Date().toISOString(),
                    metadata: data.metadata || {}
                  };

                  // Atomic update: add complete message and remove streaming state
                  qc.setQueryData(messagesKey(sessionId), (prev = []) => [...prev, completeMessage]);
                  map.delete(data.message_id);
                }

                return map;
              });
            }
            break;
          }
          case 'stream_chunk': {
            // Legacy streaming format - convert to ai_stream format for consistency
            setStreamingMessages((prev) => {
              const map = new Map(prev);
              const m = map.get(data.message_id) || { id: data.message_id, content: '', isStreaming: true };
              const updatedMessage = {
                ...m,
                content: m.content + (data.chunk || ''),
                lastUpdated: Date.now()
              };
              map.set(data.message_id, updatedMessage);
              return map;
            });
            break;
          }
          case 'stream_end': {
            // Legacy streaming completion - convert to ai_stream format for consistency
            setStreamingMessages((prev) => {
              const map = new Map(prev);
              const streamingMessage = map.get(data.message_id);

              if (streamingMessage) {
                const completeMessage = {
                  id: data.message_id,
                  role: 'assistant',
                  content: streamingMessage.content,
                  created_at: new Date().toISOString(),
                  metadata: data.metadata || {}
                };

                // Atomic update: add complete message and remove streaming state
                qc.setQueryData(messagesKey(sessionId), (prev = []) => [...prev, completeMessage]);
                map.delete(data.message_id);
              }

              return map;
            });
            break;
          }
          case 'message_update':
            qc.setQueryData(messagesKey(sessionId), (prev = []) =>
              prev.map((msg) => (msg.id === data.message_id ? { ...msg, ...data.updates, edited: true } : msg))
            );
            break;
          case 'message_delete':
            qc.setQueryData(messagesKey(sessionId), (prev = []) => prev.filter((m) => m.id !== data.message_id));
            break;
          case 'config_update':
            window.dispatchEvent(new CustomEvent('configUpdate', { detail: data }));
            break;
          default:
        }
      } catch (e) {
        console.error('WS parse error', e);
      }
    }, [sessionId, qc]), // Stable dependencies
  });

  // ---------------------------------------------------
  // 4. Mutations (send / edit / delete)
  // ---------------------------------------------------
  const sendMutation = useMutation({
    mutationFn: async ({ content, metadata = {} }) => {
      // Map frontend metadata to backend schema fields
      const payload = {
        role: 'user', // Required field that was missing
        content,
        code_snippets: metadata.code_snippets || [],
        referenced_files: metadata.referenced_files || [],
        referenced_chunks: metadata.referenced_chunks || [],
        applied_commands: metadata.applied_commands || {},
        // Include any knowledge context if present
        ...(metadata.knowledge_context && { knowledge_context: metadata.knowledge_context }),
      };

      const { data } = await chatAPI.sendMessage(sessionId, payload);
      return data;
    },
    // Remove onSuccess - the message will be added via WebSocket broadcast
    // onSuccess: (newMsg) => {
    //   qc.setQueryData(messagesKey(sessionId), (prev = []) => [...prev, newMsg]);
    // },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, content }) => chatAPI.editMessage(id, content).then((r) => r.data),
    onMutate: async ({ id, content }) => {
      await qc.cancelQueries({ queryKey: messagesKey(sessionId) });
      const prev = qc.getQueryData(messagesKey(sessionId));
      qc.setQueryData(messagesKey(sessionId), (old = []) =>
        old.map((m) => (m.id === id ? { ...m, content, edited: true } : m))
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => qc.setQueryData(messagesKey(sessionId), ctx.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: messagesKey(sessionId) }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => chatAPI.deleteMessage(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: messagesKey(sessionId) });
      const prev = qc.getQueryData(messagesKey(sessionId));
      qc.setQueryData(messagesKey(sessionId), (old = []) => old.filter((m) => m.id !== id));
      return { prev };
    },
    onError: (_err, _id, ctx) => qc.setQueryData(messagesKey(sessionId), ctx.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: messagesKey(sessionId) }),
  });

  // Typing indicator
  const sendTypingIndicator = useCallback(
    (isTyping) => {
      send({ type: 'typing', typing: isTyping });
    },
    [send]
  );

  // Cleanup old streaming messages to prevent memory leaks
  useEffect(() => {
    const cleanup = () => {
      const now = Date.now();
      const staleThreshold = 5 * 60 * 1000; // 5 minutes

      setStreamingMessages(prev => {
        const map = new Map();
        let cleaned = false;

        for (const [id, stream] of prev) {
          // Keep messages that are still streaming or recently updated
          if (stream.isStreaming || (now - (stream.lastUpdated || 0)) < staleThreshold) {
            map.set(id, stream);
          } else {
            cleaned = true;
          }
        }

        if (cleaned) {
          console.log('Cleaned up stale streaming messages');
        }

        return map;
      });
    };

    const interval = setInterval(cleanup, 2 * 60 * 1000); // Cleanup every 2 minutes
    return () => clearInterval(interval);
  }, []);

  return useMemo(
    () => ({
      sessionId,
      connectionState,
      messages,
      streamingMessages,
      typingUsers,
      historyLoading: historyLoading || sessionLoading,
      sendMessage: (c, m) => sendMutation.mutateAsync({ content: c, metadata: m }),
      editMessage: (id, content) => editMutation.mutateAsync({ id, content }),
      deleteMessage: (id) => deleteMutation.mutateAsync(id),
      sendTypingIndicator,
    }),
    [
      sessionId,
      connectionState,
      messages,
      streamingMessages,
      typingUsers,
      historyLoading,
      sessionLoading,
      sendMutation,
      editMutation,
      deleteMutation,
      sendTypingIndicator,
    ]
  );
}
