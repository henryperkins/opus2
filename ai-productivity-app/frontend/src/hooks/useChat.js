// useChat.js – Chat WebSocket + React-Query powered hook
//-------------------------------------------------------
// Replaces the earlier monolithic stateful version with:
//   • React-Query cache for historical messages
//   • useWebSocketChannel for live streaming / updates
//   • Optimistic mutations for edit / delete

import { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import chatAPI from '../api/chat';
import { useAuth } from './useAuth';
import { useWebSocketChannel } from './useWebSocketChannel';
import { useConfig } from './useConfig';

// -----------------------
// Helpers & keys
// -----------------------
const messagesKey = (sessionId) => ['messages', sessionId];

// -----------------------
// Hook
// -----------------------
export function useChat(projectId, preferredSessionId = null) {
  const { user, loading: authLoading } = useAuth();
  const { config } = useConfig();
  const qc = useQueryClient();

  const [typingUsers, setTypingUsers] = useState(new Set());
  const [streamingMessages, setStreamingMessages] = useState(new Map());

  // ---------------------------------------------------
  // 1. Session bootstrap (React Query-driven approach)
  // ---------------------------------------------------
  const { data: sessionData, isLoading: sessionLoading } = useQuery({
    queryKey: ['session', projectId, preferredSessionId],
    queryFn: async () => {
      if (!projectId || authLoading || !user) return null;

      const cached = qc.getQueryData(['session', projectId])?.id;
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
          case 'stream_chunk': {
            setStreamingMessages((prev) => {
              const map = new Map(prev);
              const m = map.get(data.message_id) || { id: data.message_id, content: '', isStreaming: true };
              m.content += data.chunk;
              map.set(data.message_id, m);
              return map;
            });
            break;
          }
          case 'stream_end': {
            setStreamingMessages((prev) => {
              const map = new Map(prev);
              const m = map.get(data.message_id);
              if (m) {
                m.isStreaming = false;
                qc.setQueryData(messagesKey(sessionId), (prev = []) => [...prev, m]);
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
    onSuccess: (newMsg) => {
      qc.setQueryData(messagesKey(sessionId), (prev = []) => [...prev, newMsg]);
    },
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
