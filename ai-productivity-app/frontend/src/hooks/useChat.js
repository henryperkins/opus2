/* global WebSocket */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './useAuth';
import client from '../api/client';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api';

export const useChat = (projectId) => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [connectionState, setConnectionState] = useState('disconnected');
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [error, setError] = useState(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const maxReconnectAttempts = 5;
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (authLoading || !user || !projectId) {
      setConnectionState('disconnected');
      return;
    }
  
    let isCancelled = false;
    let currentWs = null;
  
    const connect = async () => {
      setConnectionState('connecting');
      setError(null);
  
      try {
        // 1. Create a new session
        const sessionResponse = await client.post(`/api/chat/sessions`, {
          project_id: projectId,
        });
  
        if (isCancelled) return;
  
        const newSessionId = sessionResponse.data.id;
        setSessionId(newSessionId);
        setMessages([]); // Clear messages for new session
  
        // 2. Connect to WebSocket
        const wsUrl = `${WS_BASE_URL}/chat/ws/sessions/${newSessionId}`;
        const ws = new WebSocket(wsUrl);
        currentWs = ws;
        wsRef.current = ws;
  
        ws.onopen = () => {
          if (isCancelled) return;
          console.log('WebSocket connected to session:', newSessionId);
          setConnectionState('connected');
          setReconnectAttempts(0);
        };
  
        ws.onmessage = (event) => {
          if (isCancelled) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
              setMessages((prev) => [...prev, data.message]);
            } else if (data.type === 'typing') {
              setTypingUsers((prev) => {
                const newSet = new Set(prev);
                data.typing ? newSet.add(data.user_id) : newSet.delete(data.user_id);
                return newSet;
              });
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };
  
        ws.onclose = (event) => {
          if (isCancelled) return;
          console.log('WebSocket disconnected. Code:', event.code);
          setConnectionState('disconnected');
          // Reconnection logic can be added here if needed
        };
  
        ws.onerror = (event) => {
          if (isCancelled) return;
          console.error('WebSocket error:', event);
          setError('Connection error');
          setConnectionState('error');
        };
  
      } catch (err) {
        if (isCancelled) return;
        console.error('Failed to create session or connect:', err);
        setError('Failed to initialize chat session');
        setConnectionState('error');
      }
    };
  
    connect();
  
    return () => {
      isCancelled = true;
      if (currentWs) {
        console.log('Closing WebSocket for session:', sessionId);
        currentWs.close();
      }
      wsRef.current = null;
      setSessionId(null);
      setMessages([]);
    };
  }, [projectId, user, authLoading]); // Effect dependencies

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
