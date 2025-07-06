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

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import debounce from 'lodash.debounce';

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
  maxRetries = 50, // Absolute maximum to prevent unbounded reconnections
  protocols,
  onFallback, // optional callback fired after permanent failure to allow REST polling
  debounceMs = 100, // Add debouncing to prevent rapid reconnections
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
  const globalRetryRef = useRef(0); // Track total reconnection attempts
  const queueRef = useRef([]);
  const timerRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const messageBuffer = useRef([]);

  // Update the onMessage ref when it changes
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  // Process buffered messages with optimized batching
  useEffect(() => {
    const interval = setInterval(() => {
      if (messageBuffer.current.length > 0 && onMessageRef.current) {
        // Process messages in smaller batches to prevent blocking
        const batchSize = Math.min(5, messageBuffer.current.length);
        const batch = messageBuffer.current.splice(0, batchSize);
        
        // Use requestAnimationFrame for better performance
        requestAnimationFrame(() => {
          batch.forEach((data, index) => {
            try {
              // Create a synthetic event for compatibility
              const syntheticEvent = { data: JSON.stringify(data) };
              onMessageRef.current(syntheticEvent);
            } catch (error) {
              console.error(`Failed to process buffered message at index ${index}:`, error);
              // Continue processing remaining messages instead of breaking
            }
          });
        });
      }
    }, 50); // Reduced interval for more responsive processing

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

  // Enhanced memoization with connection stability tracking
  const connectionKey = useMemo(() => {
    // Include state to prevent reconnection during stable connections
    const key = JSON.stringify({ path, protocols: protocols || [], retry });
    console.log(`🔌 WebSocket connection key updated: ${key}`);
    return key;
  }, [path, protocols, retry]);

  // Track connection stability to prevent unnecessary reconnections
  const connectionStable = useRef(false);
  const lastSuccessfulPath = useRef(null);

  // Create debounced connect function to prevent rapid reconnections
  const debouncedConnect = useMemo(
    () => debounce((connectFn) => {
      if (connectFn) connectFn();
    }, debounceMs),
    [debounceMs]
  );

  // Enhanced connection reuse logic
  const shouldReuseConnection = useCallback((newPath) => {
    const currentWs = wsRef.current;
    if (!currentWs) return false;
    
    const isConnected = currentWs.readyState === WebSocket.OPEN;
    const isSamePath = lastSuccessfulPath.current === newPath;
    const isStable = connectionStable.current;
    
    if (isConnected && isSamePath && isStable) {
      console.log(`🔌 WebSocket: reusing stable connection to ${newPath}`);
      return true;
    }
    
    return false;
  }, []);

  useEffect(() => {
    let aborted = false;

    // If path is falsy *do not* touch an existing live socket.
    // This prevents the null→valid→null oscillation that closes
    // and re-opens the connection every render.
    if (!path) {
      return () => {};       // keep current socket alive
    }

    // Enhanced connection reuse with stability tracking
    if (shouldReuseConnection(path)) {
      return () => { };
    }

    // Reset stability on new connection attempts
    connectionStable.current = false;
    console.log(`🔌 WebSocket useEffect: setting up connection to ${path}`);

    function connect() {
      if (aborted) return;

      setState('connecting');
      const ws = new WebSocket(buildWsUrl(path), protocols);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected: ${ws.url}`);
        retryRef.current = 0;
        globalRetryRef.current = 0; // Reset global counter on successful connection
        setState('connected');
        
        // Track successful connection for stability
        lastSuccessfulPath.current = path;
        
        // Mark connection as stable after a brief delay
        setTimeout(() => {
          if (!aborted && ws.readyState === WebSocket.OPEN) {
            connectionStable.current = true;
            console.log(`🔌 WebSocket marked as stable: ${path}`);
          }
        }, 1000);
        
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
              try {
                onMessageRef.current(evt);
              } catch (handlerError) {
                console.error('Failed to process WebSocket message in direct fallback:', handlerError);
              }
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
            // Still try to process the raw event
            try {
              onMessageRef.current(evt);
            } catch (handlerError) {
              console.error('Failed to process WebSocket message in handler:', handlerError);
            }
          }
        }
      };

      ws.onclose = (evt) => {
        if (aborted) return;
        setState('disconnected');
        setLastCloseEvent(evt);
        
        // Reset stability tracking on closure
        connectionStable.current = false;

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
        const withinGlobalLimit = globalRetryRef.current < maxRetries;

        const shouldRetry =
          (isBackendRestart || evt.code === 1005 || // No status
            (evt.code >= 1000 && evt.code < 4000 && evt.code !== 1000 && evt.code !== 1001)) &&
          (withinRetryBudget || isBackendRestart) &&
          withinGlobalLimit; // Always respect global limit

        if (shouldRetry) {
          // Reset counter when we detect a backend restart so that we don't
          // prematurely exhaust the budget.
          if (isBackendRestart) {
            retryRef.current = 0;

            // Poll health-check before attempting to reconnect so we don't
            // spam connection attempts during long deploys.
            let pollInterval = 2000; // Start with 2s
            const poll = setInterval(async () => {
              const healthy = await checkBackendHealth();
              if (healthy) {
                clearInterval(poll);
                connect();
              } else {
                // Increase polling interval to reduce load during extended outages
                pollInterval = Math.min(pollInterval * 1.2, 10000); // Max 10s
                clearInterval(poll);
                setTimeout(() => {
                  const newPoll = setInterval(async () => {
                    const isHealthy = await checkBackendHealth();
                    if (isHealthy) {
                      clearInterval(newPoll);
                      connect();
                    }
                  }, pollInterval);
                }, pollInterval);
              }
            }, pollInterval);
            return; // Exit early – will reconnect from poll
          }

          // Exponential backoff: 1s * 1.5^n with 30 s cap + jitter.
          const baseDelay = Math.min(30000, 1000 * Math.pow(1.5, retryRef.current));
          const jitter = Math.random() * 1000;
          const delay = baseDelay + jitter;

          retryRef.current += 1;
          globalRetryRef.current += 1;
          console.warn(
            `WebSocket reconnecting in ${Math.round(delay / 1000)}s (attempt ${retryRef.current}${withinRetryBudget ? `/${retry}` : ''}, global: ${globalRetryRef.current}/${maxRetries})`
          );
          timerRef.current = setTimeout(connect, delay);
        } else {
          const reason = !withinGlobalLimit 
            ? `global retry limit (${maxRetries}) exceeded`
            : `retry limit (${retry}) exceeded`;
          console.error(`WebSocket connection failed: ${reason}. Giving up.`);
          setState('error');
          if (typeof onFallback === 'function') {
            onFallback(evt, { attempts: retryRef.current, globalAttempts: globalRetryRef.current });
          }
        }
      };

      ws.onerror = (evt) => {
        console.error(`WebSocket error: url=${ws?.url}, readyState=${ws?.readyState}`, evt);
        setState('error');
      };
    }

    // Use debounced connection to prevent rapid reconnections during development
    debouncedConnect(connect);

    return () => {
      // Only tear down when the next render requests **another**
      // non-null path.  Skip if it's the transient null sentinel.
      if (path && path !== lastSuccessfulPath.current) {
        aborted = true;
        clearTimeout(timerRef.current);
        connectionStable.current = false;
        console.log(`🔌 WebSocket cleanup: closing ${path}`);
        close();
      }
    };
  }, [connectionKey, debouncedConnect, close]); // Use memoized connection key instead of individual params

  return { state, send, close, socket: wsRef.current, lastCloseEvent };
}

// HMR: Keep WebSocket connections stable between updates
if (import.meta.hot) {
  import.meta.hot.accept();
  import.meta.hot.dispose(() => {
    console.log('[HMR] Disposing WebSocket hook module');
  });
}
