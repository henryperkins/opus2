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
        // 1. Create a new session
        const sessionResponse = await client.post(`/api/chat/sessions`, {
          project_id: projectId,
        });
  
        if (isCancelled) return;
  
        const newSessionId = sessionResponse.data.id;
        setSessionId(newSessionId);
        setMessages([]); // Clear messages for new session
  
        // 2. Connect to WebSocket
        const wsUrl = `${WS_BASE_URL.replace('http', 'ws')}/chat/ws/sessions/${newSessionId}`;
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
                    // Move completed message to main messages array
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
                // Also remove from streaming messages if it exists
                setStreamingMessages((prev) => {
                  const newMap = new Map(prev);
                  newMap.delete(data.message_id);
                  return newMap;
                });
                break;
                
              case 'error':
                console.error('WebSocket error received:', data.error);
                setError(data.error.message || 'An error occurred');
                
                // If error is related to a specific message, stop its streaming
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

  // Stop streaming for a specific message
  const stopStreaming = useCallback((messageId) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const message = {
      type: 'stop_stream',
      message_id: messageId
    };

    wsRef.current.send(JSON.stringify(message));
  }, []);

  // Get combined messages (regular + streaming)
  const getAllMessages = useCallback(() => {
    const streamingArray = Array.from(streamingMessages.values());
    return [...messages, ...streamingArray].sort((a, b) => {
      const timeA = new Date(a.created_at || a.timestamp || 0);
      const timeB = new Date(b.created_at || b.timestamp || 0);
      return timeA - timeB;
    });
  }, [messages, streamingMessages]);

  // Check if any message is currently streaming
  const hasStreamingMessages = streamingMessages.size > 0;

  return {
    sessionId,
    messages,
    streamingMessages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator,
    stopStreaming,
    getAllMessages,
    hasStreamingMessages,
    error
  };
};
