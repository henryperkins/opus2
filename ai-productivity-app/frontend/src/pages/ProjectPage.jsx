import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ErrorBoundary from '../components/common/ErrorBoundary';
import SkeletonLoader from '../components/common/SkeletonLoader';
import { analyticsAPI } from '../api/analytics';
import { knowledgeAPI } from '../api/knowledge';
import useProjectStore from '../stores/projectStore';
import ProjectHeader from '../components/projects/ProjectHeader';
import QuickActions from '../components/projects/QuickActions';
import MetricsPanel from '../components/projects/MetricsPanel';
import ActivityTimeline from '../components/projects/ActivityTimeline';

export default function ProjectPage() {
  const { projectId } = useParams();
  const {
    currentProject: project,
    loading,
    error,
    fetchProject
  } = useProjectStore();

  const [metrics, setMetrics] = useState(null);
  const [kbStats, setKbStats] = useState(null);

  useEffect(() => {
    fetchProject(projectId);
  }, [projectId, fetchProject]);

  useEffect(() => {
    (async () => {
      try {
        const [metricsResponse, kbResponse] = await Promise.allSettled([
          analyticsAPI.getQualityMetrics(projectId),
          knowledgeAPI.getSummary(projectId)
        ]);

        if (metricsResponse.status === 'fulfilled') {
          setMetrics(metricsResponse.value.data || metricsResponse.value);
        }
        
        if (kbResponse.status === 'fulfilled') {
          setKbStats(kbResponse.value);
        }
      } catch (e) {
        console.warn('Error loading metrics or knowledge stats:', e);
      }
    })();
  }, [projectId]);

  if (loading) {
    return <SkeletonLoader type="card" count={3} />;
  }
  
  if (error || !project) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <p className="text-red-600">{error || 'Project not found'}</p>
      </div>
    );
  }

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <ProjectHeader project={project} />

      <QuickActions projectId={projectId} />

      <MetricsPanel quality={metrics} kb={kbStats} />

      <ErrorBoundary>
        <ActivityTimeline projectId={projectId} />
      </ErrorBoundary>
    </main>
  );
}