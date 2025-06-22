/* global WebSocket */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './useAuth';
import client from '../api/client';
import { nanoid } from 'nanoid';

// Helper function to get cookie value
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
};

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const useChat = (projectId, preferredSessionId = null) => {
  const [sessionId, setSessionId] = useState(preferredSessionId);
  const [messages, setMessages] = useState([]);
  const [connectionState, setConnectionState] = useState('disconnected');
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [error, setError] = useState(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [streamingMessages, setStreamingMessages] = useState(new Map());

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
        let newSessionId = preferredSessionId;

        if (newSessionId) {
          try {
            const res = await client.get(`/api/chat/sessions/${newSessionId}`);
            if (res.data.project_id !== Number(projectId)) {
              console.warn(
                `Session ${newSessionId} does not belong to project ${projectId}.`
              );
              newSessionId = null;
            }
          } catch (err) {
            console.error(`Failed to validate session ${newSessionId}:`, err);
            newSessionId = null;
          }
        }

        if (!newSessionId) {
          const sessionData = await client.post('/api/chat/sessions', {
            project_id: Number(projectId),
          });
          newSessionId = sessionData.data.id;
        }

        if (isCancelled || !newSessionId) return;
        setSessionId(newSessionId);

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsBaseUrl = API_BASE_URL.replace('http://', `${protocol}//`).replace('https://', `${protocol}//`);
        
        const token = localStorage.getItem('token');
        const wsUrl = `${wsBaseUrl}/api/chat/ws/sessions/${newSessionId}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
        console.log('Connecting to WebSocket:', wsUrl);

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

            switch (data.type) {
              case 'message':
                setMessages((prev) => [...prev, data.message]);
                break;

              case 'typing':
                setTypingUsers((prev) => {
                  const newSet = new Set(prev);
                  data.typing ? newSet.add(data.user_id) : newSet.delete(data.user_id);
                  return newSet;
                });
                break;

              case 'stream_chunk':
                setStreamingMessages((prev) => {
                  const newMap = new Map(prev);
                  const existingMessage = newMap.get(data.message_id) || {
                    id: data.message_id,
                    content: '',
                    isStreaming: true,
                    metadata: data.metadata || {}
                  };

                  existingMessage.content += data.chunk;
                  newMap.set(data.message_id, existingMessage);
                  return newMap;
                });
                break;

              case 'stream_end':
                setStreamingMessages((prev) => {
                  const newMap = new Map(prev);
                  const streamingMessage = newMap.get(data.message_id);

                  if (streamingMessage) {
                    const finalMessage = {
                      ...streamingMessage,
                      isStreaming: false,
                      completed_at: new Date().toISOString()
                    };

                    setMessages((prevMessages) => [...prevMessages, finalMessage]);
                    newMap.delete(data.message_id);
                  }

                  return newMap;
                });
                break;

              case 'message_update':
                setMessages((prev) =>
                  prev.map(msg =>
                    msg.id === data.message_id
                      ? { ...msg, ...data.updates, edited: true, edited_at: new Date().toISOString() }
                      : msg
                  )
                );
                break;

              case 'message_delete':
                setMessages((prev) => prev.filter(msg => msg.id !== data.message_id));
                setStreamingMessages((prev) => {
                  const newMap = new Map(prev);
                  newMap.delete(data.message_id);
                  return newMap;
                });
                break;

              case 'error':
                console.error('WebSocket error received:', data.error);
                setError(data.error.message || 'An error occurred');

                if (data.message_id) {
                  setStreamingMessages((prev) => {
                    const newMap = new Map(prev);
                    const streamingMessage = newMap.get(data.message_id);

                    if (streamingMessage) {
                      streamingMessage.isStreaming = false;
                      streamingMessage.error = data.error.message;
                    }

                    return newMap;
                  });
                }
                break;

              default:
                console.warn('Unknown WebSocket message type:', data.type);
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
            setError('Failed to process message from server');
          }
        };

        ws.onclose = (event) => {
          if (isCancelled) return;
          console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason);

          if (event.code === 1008) {
            console.error('WebSocket authentication failed - missing or invalid token');
            setError('Authentication failed. Please log in again.');
          } else if (event.code === 1006) {
            console.error('WebSocket connection closed abnormally - server may be down');
            setError('Connection failed. Please check if the server is running.');
          }

          setConnectionState('disconnected');
          wsRef.current = null;

          // Implement reconnection logic
          if (reconnectAttempts < maxReconnectAttempts && event.code !== 1008) {
            const backoffDelay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            console.log(`Reconnecting in ${backoffDelay}ms... (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
            
            reconnectTimeoutRef.current = setTimeout(() => {
              if (!isCancelled) {
                setReconnectAttempts(prev => prev + 1);
                connect();
              }
            }, backoffDelay);
          } else if (reconnectAttempts >= maxReconnectAttempts) {
            setError('Max reconnection attempts reached. Please refresh the page.');
          }
        };

        ws.onerror = (error) => {
          if (isCancelled) return;
          console.error('WebSocket error:', error);
          setConnectionState('error');
          setError('Connection error occurred');
        };

      } catch (err) {
        if (isCancelled) return;
        console.error('Failed to establish connection:', err);
        setConnectionState('error');
        setError(err.response?.data?.detail || err.message || 'Failed to connect');
      }
    };

    connect();

    return () => {
      isCancelled = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (currentWs && currentWs.readyState === WebSocket.OPEN) {
        currentWs.close(1000, 'Component unmounting');
      }
    };
  }, [projectId, preferredSessionId, user, authLoading, reconnectAttempts]);

  // Send message function that returns a Promise with the message ID
  const sendMessage = useCallback((content, metadata = {}) => {
    return new Promise((resolve, reject) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      // Generate temporary ID for optimistic update
      const tempId = `tmp-${nanoid()}`;
      
      // Create optimistic message
      const optimisticMessage = {
        id: tempId,
        role: 'user',
        content,
        metadata,
        created_at: new Date().toISOString(),
        user_id: user?.id,
        session_id: sessionId
      };

      // Add to messages immediately
      setMessages(prev => [...prev, optimisticMessage]);

      // Create message handler for this specific message
      const messageHandler = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'message' && data.message.content === content) {
            // Replace temporary ID with real ID
            setMessages(prev => 
              prev.map(msg => 
                msg.id === tempId 
                  ? { ...msg, id: data.message.id }
                  : msg
              )
            );
            
            // Clean up listener and resolve
            wsRef.current?.removeEventListener('message', messageHandler);
            resolve(data.message.id);
          }
        } catch (err) {
          console.error('Error handling message response:', err);
        }
      };

      // Add temporary listener for the response
      wsRef.current.addEventListener('message', messageHandler);

      // Send the message
      try {
        wsRef.current.send(JSON.stringify({
          type: 'message',
          content,
          metadata
        }));

        // Set a timeout to reject if no response
        setTimeout(() => {
          wsRef.current?.removeEventListener('message', messageHandler);
          reject(new Error('Message send timeout'));
        }, 5000);
      } catch (err) {
        wsRef.current?.removeEventListener('message', messageHandler);
        // Remove optimistic message on error
        setMessages(prev => prev.filter(msg => msg.id !== tempId));
        reject(err);
      }
    });
  }, [sessionId, user]);

  // Send typing indicator
  const sendTypingIndicator = useCallback((isTyping) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      type: 'typing',
      typing: isTyping
    }));
  }, []);

  // Edit message
  const editMessage = useCallback((messageId, newContent) => {
    setMessages(prev =>
      prev.map(msg =>
        msg.id === messageId
          ? { ...msg, content: newContent, edited: true }
          : msg
      )
    );
    // TODO: Send edit to server
  }, []);

  // Delete message
  const deleteMessage = useCallback((messageId) => {
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
    // TODO: Send delete to server
  }, []);

  return {
    sessionId,
    messages,
    connectionState,
    typingUsers,
    error,
    sendMessage,
    sendTypingIndicator,
    editMessage,
    deleteMessage,
    streamingMessages
  };
};