// useChat.js – Chat WebSocket + React-Query powered hook
//-------------------------------------------------------
// Replaces the earlier monolithic stateful version with:
//   • React-Query cache for historical messages
//   • useWebSocketChannel for live streaming / updates
//   • Optimistic mutations for edit / delete

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';
import { useAuth } from './useAuth';
import { useWebSocketChannel } from './useWebSocketChannel';

// -----------------------
// Helpers & keys
// -----------------------
const messagesKey = (sessionId) => ['messages', sessionId];

// -----------------------
// Hook
// -----------------------
export function useChat(projectId, preferredSessionId = null) {
  const { user, loading: authLoading } = useAuth();
  const qc = useQueryClient();

  const [sessionId, setSessionId] = useState(preferredSessionId);
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [streamingMessages, setStreamingMessages] = useState(new Map());

  // ---------------------------------------------------
  // 1. Session bootstrap (fetch or create)
  // ---------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    async function ensureSession() {
      if (!projectId || authLoading || !user) return;

      let sid = preferredSessionId;
      try {
        if (sid) {
          const { data } = await client.get(`/api/chat/sessions/${sid}`);
          if (data.project_id !== Number(projectId)) sid = null;
        }

        if (!sid) {
          const { data } = await client.post('/api/chat/sessions', {
            project_id: Number(projectId),
          });
          sid = data.id;
        }
        if (!cancelled) setSessionId(sid);
      } catch {
        /* swallow – ErrorBoundary higher up will display */
      }
    }

    ensureSession();
    return () => {
      cancelled = true;
    };
  }, [projectId, preferredSessionId, authLoading, user]);

  // ---------------------------------------------------
  // 2. Historical messages
  // ---------------------------------------------------
  const {
    data: messages = [],
    isFetching: historyLoading,
  } = useQuery({
    queryKey: messagesKey(sessionId),
    queryFn: () => client.get(`/api/chat/sessions/${sessionId}/messages`).then((r) => r.data),
    enabled: !!sessionId,
    staleTime: 0,
  });

  // ---------------------------------------------------
  // 3. Live WebSocket connection
  // ---------------------------------------------------
  const { state: connectionState, send } = useWebSocketChannel({
    path: sessionId ? `/api/chat/ws/sessions/${sessionId}` : null,
    retry: 5,
    onMessage: (event) => {
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
          default:
        }
      } catch (e) {
        console.error('WS parse error', e);
      }
    },
  });

  // ---------------------------------------------------
  // 4. Mutations (send / edit / delete)
  // ---------------------------------------------------
  const sendMutation = useMutation(
    async ({ content, metadata }) => {
      const { data } = await client.post(`/api/chat/sessions/${sessionId}/messages`, {
        content,
        metadata,
      });
      return data;
    },
    {
      onSuccess: (newMsg) => {
        qc.setQueryData(messagesKey(sessionId), (prev = []) => [...prev, newMsg]);
      },
    }
  );

  const editMutation = useMutation(
    ({ id, content }) => client.patch(`/api/chat/messages/${id}`, { content }).then((r) => r.data),
    {
      onMutate: async ({ id, content }) => {
        await qc.cancelQueries(messagesKey(sessionId));
        const prev = qc.getQueryData(messagesKey(sessionId));
        qc.setQueryData(messagesKey(sessionId), (old = []) =>
          old.map((m) => (m.id === id ? { ...m, content, edited: true } : m))
        );
        return { prev };
      },
      onError: (_err, _vars, ctx) => qc.setQueryData(messagesKey(sessionId), ctx.prev),
      onSettled: () => qc.invalidateQueries(messagesKey(sessionId)),
    }
  );

  const deleteMutation = useMutation(
    (id) => client.delete(`/api/chat/messages/${id}`),
    {
      onMutate: async (id) => {
        await qc.cancelQueries(messagesKey(sessionId));
        const prev = qc.getQueryData(messagesKey(sessionId));
        qc.setQueryData(messagesKey(sessionId), (old = []) => old.filter((m) => m.id !== id));
        return { prev };
      },
      onError: (_err, _id, ctx) => qc.setQueryData(messagesKey(sessionId), ctx.prev),
      onSettled: () => qc.invalidateQueries(messagesKey(sessionId)),
    }
  );

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
      historyLoading,
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
      sendMutation.mutateAsync,
      editMutation.mutateAsync,
      deleteMutation.mutateAsync,
      sendTypingIndicator,
    ]
  );
}
