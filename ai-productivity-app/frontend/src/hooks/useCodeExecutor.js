/*
 * useCodeExecutor.js
 * ------------------
 * Centralised client-side helper for executing code snippets through the
 * backend and sharing the results across React components.
 *
 * Responsibilities
 *  • expose executeCode(code, language, projectId, correlationId?) that
 *    returns a Promise with the execution result.
 *  • maintain a Map keyed by correlationId containing
 *      { status: 'pending'|'running'|'success'|'error',
 *        result?: {...},
 *        error?: any }
 *  • allow callers to abort a running request via abortExecution(id).
 *  • optionally cache previous identical invocations (simple hash).
 */

import { useCallback, useRef, useSyncExternalStore } from 'react';
import { nanoid } from 'nanoid';
import client from '../api/client';

// Polyfill AbortController for older environments
if (typeof globalThis.AbortController === 'undefined') {
  globalThis.AbortController = class AbortController {
    constructor() {
      this.signal = {
        aborted: false,
        addEventListener: (type, listener) => {
          if (type === 'abort' && !this._abortListener) {
            this._abortListener = listener;
          }
        },
        removeEventListener: (type, listener) => {
          if (type === 'abort' && this._abortListener === listener) {
            this._abortListener = null;
          }
        }
      };
    }
    abort() {
      if (!this.signal.aborted) {
        this.signal.aborted = true;
        if (this.signal._abortListener) {
          this.signal._abortListener();
        }
      }
    }
  };
}

// ----------------------------------------------------------------------------
// Global singleton store – lightweight replacement for context
// ----------------------------------------------------------------------------

const subscribers = new Set();

// resultsMap lives outside React so multiple components share the same data
const resultsMap = new Map(); // key => {status, result?, error?}

// abortControllers so we can cancel running executions
const abortControllers = new Map();

function emitChange() {
  subscribers.forEach((fn) => fn());
}

function getSnapshot() {
  return resultsMap;
}

// ----------------------------------------------------------------------------
// Hook
// ----------------------------------------------------------------------------

export function useCodeExecutor(defaultProjectId = null) {
  // Sync resultsMap updates into React components
  const results = useSyncExternalStore(
    (callback) => {
      subscribers.add(callback);
      return () => subscribers.delete(callback);
    },
    getSnapshot,
    getSnapshot
  );

  // ------------------------------------------------------------------
  // executeCode implementation
  // ------------------------------------------------------------------

  const executeCode = useCallback(
    async (code, language, projectId = defaultProjectId, correlationId = nanoid()) => {
      if (!code || !language) {
        throw new Error('executeCode: code and language are required');
      }

      // Deduplicate identical request that is already running
      const existing = resultsMap.get(correlationId);
      if (existing && existing.status === 'pending') {
        return existing.promise; // return the in-flight promise
      }

      const controller = new globalThis.AbortController();
      abortControllers.set(correlationId, controller);

      const payload = { code, language };
      if (projectId !== undefined && projectId !== null) payload.project_id = projectId;

      const executionPromise = (async () => {
        try {
          resultsMap.set(correlationId, { status: 'running' });
          emitChange();

          const { data } = await client.post('/code/execute', payload, {
            signal: controller.signal,
          });

          resultsMap.set(correlationId, { status: 'success', result: data });
          abortControllers.delete(correlationId);
          emitChange();
          return data;
        } catch (error) {
          if (controller.signal.aborted) {
            const err = new Error('Execution aborted');
            resultsMap.set(correlationId, { status: 'error', error: err });
            emitChange();
            throw err;
          }

          resultsMap.set(correlationId, { status: 'error', error });
          abortControllers.delete(correlationId);
          emitChange();
          throw error;
        }
      })();

      // store a placeholder with pending promise so duplicate calls can await
      resultsMap.set(correlationId, { status: 'pending', promise: executionPromise });
      emitChange();

      return executionPromise;
    },
    [defaultProjectId]
  );

  const abortExecution = useCallback((correlationId) => {
    const controller = abortControllers.get(correlationId);
    if (controller) {
      controller.abort();
    }
  }, []);

  return { executeCode, results, abortExecution };
}

export default useCodeExecutor;
