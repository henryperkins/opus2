// useTimeline.js – fetches recent activity timeline
// This hook encapsulates timelineAPI access so that UI components
// (pages) don’t import API modules directly, satisfying the
// no-restricted-imports ESLint rule.

import { useEffect, useState } from "react";
import { timelineAPI } from "../api/timeline";
import { useAuth } from "./useAuth";

/**
 * Fetch a list of recent timeline events for the current user.
 *
 * @param {object} params Optional query params (e.g. { limit: 200 })
 * @returns {{ events: Array, loading: boolean, error: string|null }}
 */
export function useTimeline(params = { limit: 200 }) {
  const { user, loading: authLoading } = useAuth();

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (authLoading || !user) return;

    let cancelled = false;

    const fetchEvents = async () => {
      setLoading(true);
      try {
        const data = await timelineAPI.list(params);
        if (!cancelled) {
          setEvents(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchEvents();

    return () => {
      cancelled = true;
    };
  }, [authLoading, user, params]);

  return { events, loading, error };
}
