/* useWebSocketChannel.js
 * ---------------------------------------------------------
 * Small reusable hook that manages a resilient WebSocket
 * connection with cookie-based authentication.
 *
 * Features
 *   • automatic exponential-backoff reconnect with jitter
 *   • status tracking: 'connecting' | 'open' | 'closed' | 'error'
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
  const [state, setState] = useState('connecting'); // connecting | open | closed | error
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
      setState('closed');
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
        setState('open');
        // flush queue
        queueRef.current.forEach((m) => send(m));
        queueRef.current = [];
      };

      ws.onmessage = (evt) => {
        // Performance monitoring: throttle message handling to prevent blocking
        const startTime = performance.now();

        if (onMessageRef.current) {
          // Use requestIdleCallback if available, otherwise setTimeout
          if (window.requestIdleCallback) {
            window.requestIdleCallback(() => {
              onMessageRef.current(evt);
              const duration = performance.now() - startTime;
              if (duration > 50) {
                console.warn(`🔌 WebSocket message handler took ${duration.toFixed(1)}ms - consider optimizing`);
              }
            });
          } else {
            setTimeout(() => {
              onMessageRef.current(evt);
              const duration = performance.now() - startTime;
              if (duration > 50) {
                console.warn(`🔌 WebSocket message handler took ${duration.toFixed(1)}ms - consider optimizing`);
              }
            }, 0);
          }
        }
      };

      ws.onclose = (evt) => {
        if (aborted) return;
        setState('closed');

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
      close();
    };
  }, [path, protocols, retry]); // Remove onMessage, close, send from deps to prevent unnecessary reconnections

  return { state, send, close, socket: wsRef.current };
}
