import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';

export function useChat(sessionId) {
    const { user } = useAuth();
    const [messages, setMessages] = useState([]);
    const [connectionState, setConnectionState] = useState('disconnected');
    const [typingUsers, setTypingUsers] = useState(new Set());
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const typingTimeoutRef = useRef(null);

    const connect = useCallback(() => {
        if (!sessionId || !user) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/sessions/${sessionId}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnectionState('connected');
            console.log('WebSocket connected');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleMessage(data);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            setConnectionState('error');
        };

        ws.onclose = () => {
            setConnectionState('disconnected');
            wsRef.current = null;

            // Attempt reconnection
            reconnectTimeoutRef.current = setTimeout(() => {
                connect();
            }, 3000);
        };
    }, [sessionId, user]);

    const handleMessage = useCallback((data) => {
        switch (data.type) {
            case 'connected':
                console.log('Connected to session:', data.session_id);
                break;

            case 'message_history':
                setMessages(data.messages);
                break;

            case 'new_message':
                setMessages(prev => [...prev, data.message]);
                break;

            case 'message_updated':
                setMessages(prev => prev.map(msg =>
                    msg.id === data.message.id
                        ? { ...msg, ...data.message }
                        : msg
                ));
                break;

            case 'message_deleted':
                setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
                break;

            case 'user_typing':
                setTypingUsers(prev => {
                    const next = new Set(prev);
                    if (data.is_typing) {
                        next.add(data.user_id);
                    } else {
                        next.delete(data.user_id);
                    }
                    return next;
                });
                break;

            case 'ai_stream':
                handleAIStream(data);
                break;
        }
    }, []);

    const handleAIStream = useCallback((data) => {
        if (data.done) {
            // Final message
            setMessages(prev => [...prev, data.message]);
        } else {
            // Streaming update
            setMessages(prev => {
                const last = prev[prev.length - 1];
                if (last && last.id === data.message_id && last.role === 'assistant') {
                    return [
                        ...prev.slice(0, -1),
                        { ...last, content: last.content + data.content }
                    ];
                } else {
                    // First chunk
                    return [...prev, {
                        id: data.message_id,
                        content: data.content,
                        role: 'assistant',
                        created_at: new Date().toISOString()
                    }];
                }
            });
        }
    }, []);

    const sendMessage = useCallback((content, metadata = {}) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }

        wsRef.current.send(JSON.stringify({
            type: 'message',
            content,
            metadata
        }));
    }, []);

    const editMessage = useCallback((messageId, content) => {
        if (!wsRef.current) return;

        wsRef.current.send(JSON.stringify({
            type: 'edit_message',
            message_id: messageId,
            content
        }));
    }, []);

    const deleteMessage = useCallback((messageId) => {
        if (!wsRef.current) return;

        wsRef.current.send(JSON.stringify({
            type: 'delete_message',
            message_id: messageId
        }));
    }, []);

    const sendTypingIndicator = useCallback((isTyping) => {
        if (!wsRef.current) return;

        // Clear previous timeout
        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }

        wsRef.current.send(JSON.stringify({
            type: 'typing',
            is_typing: isTyping
        }));

        // Auto-stop typing after 5 seconds
        if (isTyping) {
            typingTimeoutRef.current = setTimeout(() => {
                sendTypingIndicator(false);
            }, 5000);
        }
    }, []);

    useEffect(() => {
        connect();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (typingTimeoutRef.current) {
                clearTimeout(typingTimeoutRef.current);
            }
        };
    }, [connect]);

    return {
        messages,
        connectionState,
        typingUsers,
        sendMessage,
        editMessage,
        deleteMessage,
        sendTypingIndicator
    };
}
