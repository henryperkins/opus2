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
  onFallback, // optional callback fired after permanent failure to allow REST polling
}) {
  // `state` semantics deliberately follow the naming that the rest of the
  // frontend (ConnectionIndicator, ProjectChatPage, etc.) already relies on:
  //   connecting | connected | disconnected | error
  // Previously this hook used the native WebSocket readyState names (open /
  //   closed) which caused a mismatch – `connected` was never reported and the
  //   UI refused to send messages. Aligning the vocabulary here fixes the
  //   "Cannot send message: Not connected to server" error.
  const [state, setState] = useState('connecting');
  const [lastCloseEvent, setLastCloseEvent] = useState(null);
  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const queueRef = useRef([]);
  const timerRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const messageBuffer = useRef([]);

  // Update the onMessage ref when it changes
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  // Process buffered messages periodically
  useEffect(() => {
    const interval = setInterval(() => {
      if (messageBuffer.current.length > 0 && onMessageRef.current) {
        const messages = messageBuffer.current.splice(0);
        messages.forEach(data => {
          // Create a synthetic event for compatibility
          const syntheticEvent = { data: JSON.stringify(data) };
          onMessageRef.current(syntheticEvent);
        });
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

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

  // ----------------------------------------------------------------------
  // Helper: health-check polling – resolves to **true** when /api/health
  // returns 2xx.  Keeps requests lightweight by issuing a HEAD request.
  // ----------------------------------------------------------------------
  async function checkBackendHealth() {
    try {
      const res = await fetch('/api/health', {
        method: 'HEAD',
        credentials: 'include',
      });
      return res.ok;
    } catch {
      return false;
    }
  }

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
          // Buffer messages for batch processing to avoid performance issues
          try {
            const data = JSON.parse(evt.data);
            if (messageBuffer.current) {
              messageBuffer.current.push(data);
            } else {
              // Fallback to direct processing if buffer not available
              onMessageRef.current(evt);
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
            // Still try to process the raw event
            onMessageRef.current(evt);
          }
        }
      };

      ws.onclose = (evt) => {
        if (aborted) return;
        setState('disconnected');
        setLastCloseEvent(evt);

        // Enhanced logging for debugging
        console.warn(`WebSocket closed: code=${evt.code}, reason="${evt.reason}", wasClean=${evt.wasClean}`);

        // ------------------------------------------------------------------
        // Retry strategy ----------------------------------------------------
        // ------------------------------------------------------------------
        // We distinguish **backend restarts / transient gateway errors**
        // from *normal* user initiated closures.  Certain close-codes signal
        // the server went away unexpectedly (1006, 1011-1014).  In that
        // scenario we keep retrying *indefinitely* until the health-check
        // endpoint responds.
        //
        // For all other cases we fall back to the bounded `retry` counter to
        // avoid endless loops on permanent authentication errors (4000-4999).
        // ------------------------------------------------------------------

        const isBackendRestart =
          evt.code === 1006 || // Abnormal
          evt.code === 1011 || // Internal error
          evt.code === 1012 || // Service restart
          evt.code === 1013 || // Try again later
          evt.code === 1014;   // Bad gateway

        const withinRetryBudget = retryRef.current < retry;

        const shouldRetry =
          (isBackendRestart || evt.code === 1005 || // No status
            (evt.code >= 1000 && evt.code < 4000 && evt.code !== 1000 && evt.code !== 1001)) &&
          (withinRetryBudget || isBackendRestart); // unlimited for restarts

        if (shouldRetry) {
          // Reset counter when we detect a backend restart so that we don't
          // prematurely exhaust the budget.
          if (isBackendRestart) {
            retryRef.current = 0;

            // Poll health-check before attempting to reconnect so we don't
            // spam connection attempts during long deploys.
            const poll = setInterval(async () => {
              const healthy = await checkBackendHealth();
              if (healthy) {
                clearInterval(poll);
                connect();
              }
            }, 2000);
            return; // Exit early – will reconnect from poll
          }

          // Exponential backoff: 1s * 1.5^n with 30 s cap + jitter.
          const baseDelay = Math.min(30000, 1000 * Math.pow(1.5, retryRef.current));
          const jitter = Math.random() * 1000;
          const delay = baseDelay + jitter;

          retryRef.current += 1;
          console.warn(
            `WebSocket reconnecting in ${Math.round(delay / 1000)}s (attempt ${retryRef.current}${withinRetryBudget ? `/${retry}` : ''})`
          );
          timerRef.current = setTimeout(connect, delay);
        } else if (retryRef.current >= retry) {
          console.error(`WebSocket connection failed after ${retry} attempts. Giving up.`);
          setState('error');
          if (typeof onFallback === 'function') {
            onFallback(evt, { attempts: retryRef.current });
          }
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
  }, [path, protocols, retry, close, send, onFallback]); // Include close and send in dependencies

  return { state, send, close, socket: wsRef.current, lastCloseEvent };
}

// HMR: Keep WebSocket connections stable between updates
if (import.meta.hot) {
  import.meta.hot.accept();
  import.meta.hot.dispose(() => {
    console.log('[HMR] Disposing WebSocket hook module');
  });
}
