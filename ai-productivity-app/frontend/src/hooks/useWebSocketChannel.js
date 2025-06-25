/* useWebSocketChannel.js
 * ---------------------------------------------------------
 * Small reusable hook that manages a resilient WebSocket
 * connection with cookie-based authentication.
 *
 * Features
 *   • automatic exponential-backoff reconnect with jitter
*   • status tracking: 'connecting' | 'connected' | 'disconnected' | 'error'
 *   • helper send() that queues messages while socket connecting
 *   • optional custom onMessage handler
 */

import { useEffect, useRef, useState, useCallback } from 'react';

function buildWsUrl(path) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  let host = window.location.host;

  // Handle development environment where frontend runs on 5173 but backend on 8000
  if (host.includes(':5173')) {
    host = host.replace(':5173', ':8000');
  }

  // Ensure leading slash
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${protocol}//${host}${cleanPath}`;
}

export function useWebSocketChannel({
  path,
  onMessage,
  retry = 5,
  protocols,
}) {
  // `state` semantics deliberately follow the naming that the rest of the
  // frontend (ConnectionIndicator, ProjectChatPage, etc.) already relies on:
  //   connecting | connected | disconnected | error
  // Previously this hook used the native WebSocket readyState names (open /
  //   closed) which caused a mismatch – `connected` was never reported and the
  //   UI refused to send messages. Aligning the vocabulary here fixes the
  //   "Cannot send message: Not connected to server" error.
  const [state, setState] = useState('connecting');
  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const queueRef = useRef([]);
  const timerRef = useRef(null);
  const onMessageRef = useRef(onMessage);

  // Update the onMessage ref when it changes
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const send = useCallback(
    (payload) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(typeof payload === 'string' ? payload : JSON.stringify(payload));
      } else {
        queueRef.current.push(payload);
      }
    },
    []
  );

  const close = useCallback(() => {
    console.log(`🔌 WebSocket close() called`);
    if (wsRef.current) wsRef.current.close(1000, 'client-close');
    clearTimeout(timerRef.current);
  }, []);

  useEffect(() => {
    let aborted = false;

    if (!path) {
      setState('disconnected');
      return () => { };
    }

    // Guard: prevent duplicate connections during HMR
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log(`🔌 WebSocket: reusing existing connection to ${path}`);
      return () => { };
    }

    console.log(`🔌 WebSocket useEffect: setting up connection to ${path}`);

    function connect() {
      if (aborted) return;

      setState('connecting');
      const ws = new WebSocket(buildWsUrl(path), protocols);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected: ${ws.url}`);
        retryRef.current = 0;
        setState('connected');
        // flush queue
        queueRef.current.forEach((m) => send(m));
        queueRef.current = [];
      };

      ws.onmessage = (evt) => {
        if (onMessageRef.current) {
          // Direct message handling for better mobile performance
          // Previous async wrapping was causing messages to not appear on mobile
          onMessageRef.current(evt);
        }
      };

      ws.onclose = (evt) => {
        if (aborted) return;
        setState('disconnected');

        // Enhanced logging for debugging
        console.warn(`WebSocket closed: code=${evt.code}, reason="${evt.reason}", wasClean=${evt.wasClean}`);

        // Only retry if it's not a permanent failure or user-initiated close
        // Code 1000 = normal closure, 1001 = going away, 1005 = no status code
        // Code 4000-4999 = application-specific errors that shouldn't be retried
        const shouldRetry = retryRef.current < retry &&
          evt.code !== 1000 &&
          evt.code !== 1001 &&
          evt.code < 4000; // Don't retry application-specific errors

        if (shouldRetry) {
          // Exponential backoff with jitter: 1s, 2s, 4s, 8s, 10s max
          const baseDelay = Math.min(10000, 1000 * Math.pow(2, retryRef.current));
          const jitter = Math.random() * 1000; // 0-1s jitter
          const delay = baseDelay + jitter;

          retryRef.current += 1;
          console.warn(`WebSocket reconnecting in ${Math.round(delay / 1000)}s (attempt ${retryRef.current}/${retry})`);
          timerRef.current = setTimeout(connect, delay);
        } else if (retryRef.current >= retry) {
          console.error(`WebSocket connection failed after ${retry} attempts. Giving up.`);
          setState('error');
        } else {
          console.info('WebSocket closed normally, not retrying');
        }
      };

      ws.onerror = (evt) => {
        console.error(`WebSocket error: url=${ws?.url}, readyState=${ws?.readyState}`, evt);
        setState('error');
      };
    }

    connect();

    return () => {
      aborted = true;
      console.log(`🔌 WebSocket useEffect cleanup: closing connection to ${path}`);
      clearTimeout(timerRef.current); // cancel pending reconnect
      close();
    };
  }, [path, protocols, retry, close, send]); // Include close and send in dependencies

  return { state, send, close, socket: wsRef.current };
}

// HMR: Keep WebSocket connections stable between updates
if (import.meta.hot) {
  import.meta.hot.accept();
  import.meta.hot.dispose(() => {
    console.log('[HMR] Disposing WebSocket hook module');
  });
}
