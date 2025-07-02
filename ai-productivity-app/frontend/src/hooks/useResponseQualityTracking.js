import { useState, useEffect, useCallback } from 'react';

// Hook for tracking response quality over time
export function useResponseQualityTracking(projectId) {
  const [qualityHistory, setQualityHistory] = useState([]);

  const trackResponseQuality = (messageId, metrics) => {
    const score = (
      metrics.relevance * 0.3 +
      metrics.accuracy * 0.25 +
      metrics.helpfulness * 0.2 +
      metrics.clarity * 0.15 +
      metrics.completeness * 0.1
    );

    // Store in localStorage for persistence
    const key = `quality_${projectId}_${new Date().toISOString().split('T')[0]}`;
    const existing = localStorage.getItem(key);
    const data = existing ? JSON.parse(existing) : { totalScore: 0, count: 0 };

    data.totalScore += score;
    data.count += 1;

    localStorage.setItem(key, JSON.stringify(data));
  };

  const loadQualityHistory = useCallback(() => {
    const history = [];
    const prefix = `quality_${projectId}_`;

    // Get last 30 days
    for (let i = 0; i < 30; i++) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      const key = `${prefix}${dateStr}`;

      const data = localStorage.getItem(key);
      if (data) {
        const { totalScore, count } = JSON.parse(data);
        history.unshift({
          date: dateStr,
          averageScore: totalScore / count,
          responseCount: count
        });
      }
    }

    setQualityHistory(history);
  }, [projectId]);

  useEffect(() => {
    loadQualityHistory();
  }, [loadQualityHistory]);

  return {
    qualityHistory,
    trackResponseQuality,
    refresh: loadQualityHistory
  };
}