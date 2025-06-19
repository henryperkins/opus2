/* global WebSocket */
import { useState, useEffect, useRef, useCallback } from 'react';
import client from '../api/client';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const useChat = (projectId) => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [connectionState, setConnectionState] = useState('disconnected');
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const sessionCreatedRef = useRef(false);
  const mountedRef = useRef(true);
  const cleanupRef = useRef(false);
  const initializingRef = useRef(false);

  // Create chat session
  const createSession = useCallback(async () => {
    if (!projectId || sessionCreatedRef.current || cleanupRef.current) return;

    try {
      sessionCreatedRef.current = true;
      setError(null);

      const response = await client.post(`/api/chat/sessions`, {
        project_id: projectId
      });

      if (mountedRef.current && !cleanupRef.current) {
        setSessionId(response.data.id);
        return response.data.id;
      }

      return null;
    } catch (err) {
      sessionCreatedRef.current = false;
      if (mountedRef.current && !cleanupRef.current) {
        console.error('Failed to create session:', err);
        setError('Failed to create chat session');
      }
      return null;
    }
  }, [projectId]);

  // Connect to WebSocket
  const connectWebSocket = useCallback((sessionId) => {
    if (!sessionId || wsRef.current || cleanupRef.current || !mountedRef.current) return;

    const wsUrl = `ws://localhost:8000/api/chat/ws/sessions/${sessionId}`;
    console.log('Attempting WebSocket connection to:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (mountedRef.current && !cleanupRef.current) {
        setConnectionState('connected');
        console.log('WebSocket connected to session:', sessionId);
      }
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current || cleanupRef.current) return;

      try {
        const data = JSON.parse(event.data);

        if (data.type === 'message') {
          setMessages(prev => [...prev, data.message]);
        } else if (data.type === 'typing') {
          setTypingUsers(prev => {
            const newSet = new Set(prev);
            if (data.typing) {
              newSet.add(data.user_id);
            } else {
              newSet.delete(data.user_id);
            }
            return newSet;
          });
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = (event) => {
      if (mountedRef.current && !cleanupRef.current) {
        setConnectionState('disconnected');
        console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason);
      }
      wsRef.current = null;
    };

    ws.onerror = (event) => {
      if (mountedRef.current && !cleanupRef.current) {
        console.error('WebSocket error:', event);
        setConnectionState('error');
        setError('Connection error');
      }
    };
  }, []);

  // Initialize session and WebSocket
  useEffect(() => {
    if (!projectId) return;

    let cleanup = false;

    const initializeChat = async () => {
      console.log('Initializing chat for project:', projectId);
      setConnectionState('connecting');
      const newSessionId = await createSession();
      console.log('Created session:', newSessionId);

      if (!cleanup && newSessionId) {
        console.log('Connecting WebSocket for session:', newSessionId);
        connectWebSocket(newSessionId);
      } else {
        console.log('Skipping WebSocket connection - cleanup:', cleanup, 'sessionId:', newSessionId);
      }
    };

    initializeChat();

    return () => {
      cleanup = true;
      console.log('Cleanup initiated for project:', projectId);
    };
  }, [projectId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  // Send message
  const sendMessage = useCallback((content, metadata = {}) => {
    if (!wsRef.current) {
      console.warn('WebSocket is not connected - wsRef.current is null');
      return;
    }

    console.log('WebSocket readyState:', wsRef.current.readyState, 'Expected OPEN:', WebSocket.OPEN);

    if (wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected - readyState:', wsRef.current.readyState);
      return;
    }

    const message = {
      type: 'message',
      content,
      metadata,
      project_id: projectId
    };

    wsRef.current.send(JSON.stringify(message));
  }, [projectId]);

  // Send typing indicator
  const sendTypingIndicator = useCallback((isTyping) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const message = {
      type: 'typing',
      typing: isTyping
    };

    wsRef.current.send(JSON.stringify(message));
  }, []);

  // Edit message (placeholder)
  const editMessage = useCallback((messageId, newContent) => {
    setMessages(prev =>
      prev.map(msg =>
        msg.id === messageId
          ? { ...msg, content: newContent, edited: true }
          : msg
      )
    );
  }, []);

  // Delete message (placeholder)
  const deleteMessage = useCallback((messageId) => {
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
  }, []);

  return {
    sessionId,
    messages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator,
    error
  };
};
