// Simple WebSocket instrumentation that prints a concise trace of every
// lifecycle event (open, message, close, error) **and** every outbound
// send() call.  It also decorates the socket instance with a unique
// ``_debugId`` so callers can verify they are operating on the expected
// connection.

/* eslint-disable no-console */

let _idCounter = 0;

/**
 * Attach development-time debugging listeners to a WebSocket instance.
 *
 * Usage:
 *   const ws = attachDebug(new WebSocket(url), 'CHAT');
 *
 * @param {WebSocket} ws   The WebSocket instance you just constructed.
 * @param {string}    tag  Short label that appears in the console logs.
 * @returns {WebSocket}    The **same** WebSocket instance (allows chaining).
 */
export function attachDebug(ws, tag = 'WS') {
  // Give each socket an incremental identifier so we can disambiguate
  // multiple connections that might coexist during hot-reloads or
  // reconnect attempts.
  ws._debugId = ++_idCounter; // non-enumerable is overkill here

  const prefix = `[${tag} #${ws._debugId}]`;

  const logEvent = (evt, extra = {}) => {
    console.log(`${prefix} ${evt}`, {
      url: ws.url,
      readyState: ws.readyState,
      ...extra,
    });
  };

  ws.addEventListener('open', () => logEvent('open'));
  ws.addEventListener('close', (e) =>
    logEvent('close', { code: e.code, reason: e.reason })
  );
  ws.addEventListener('error', (e) => logEvent('error', { error: e }));

  // Message events can be *very* noisy.  Uncomment the next two lines if you
  // need to see the raw traffic in the console.
  // ws.addEventListener('message', (e) =>
  //   logEvent('message ⇐', { data: e.data })
  // );

  // Wrap send() so we can observe outbound traffic and the state at send time.
  const _send = ws.send.bind(ws);
  ws.send = function patchedSend(...args) {
    logEvent('send ⇒', { data: args[0] });
    return _send(...args);
  };

  return ws;
}
