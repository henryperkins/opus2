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
    if (wsRef.current) wsRef.current.close(1000, 'client-close');
    clearTimeout(timerRef.current);
  }, []);

  useEffect(() => {
    let aborted = false;

    if (!path) {
      setState('closed');
      return () => {};
    }

    function connect() {
      if (aborted) return;

      setState('connecting');
      const ws = new WebSocket(buildWsUrl(path), protocols);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setState('open');
        // flush queue
        queueRef.current.forEach((m) => send(m));
        queueRef.current = [];
      };

      ws.onmessage = (evt) => {
        if (onMessage) onMessage(evt);
      };

      ws.onclose = (evt) => {
        if (aborted) return;
        setState('closed');
        if (retryRef.current < retry) {
          const delay = Math.min(30000, 1000 * 2 ** retryRef.current) + Math.random() * 500;
          retryRef.current += 1;
          timerRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => setState('error');
    }

    connect();

    return () => {
      aborted = true;
      close();
    };
  }, [path, protocols, onMessage, retry, close, send]);

  return { state, send, close, socket: wsRef.current };
}
