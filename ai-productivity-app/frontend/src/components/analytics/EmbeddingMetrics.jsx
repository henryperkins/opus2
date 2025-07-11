// components/analytics/EmbeddingMetrics.jsx
import { useState, useEffect } from "react";
import {
  Activity,
  Zap,
  Clock,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Database,
  Server,
} from "lucide-react";
import { analyticsAPI } from "../../api/analytics";

const MetricCard = ({
  title,
  value,
  unit = "",
  icon: Icon,
  status = "normal",
  trend = null,
}) => {
  const statusColors = {
    normal: "text-gray-900 dark:text-gray-100",
    success: "text-green-600 dark:text-green-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    error: "text-red-600 dark:text-red-400",
  };

  const statusBgColors = {
    normal: "bg-gray-50 dark:bg-gray-800",
    success: "bg-green-50 dark:bg-green-900/20",
    warning: "bg-yellow-50 dark:bg-yellow-900/20",
    error: "bg-red-50 dark:bg-red-900/20",
  };

  return (
    <div
      className={`p-4 rounded-lg border ${statusBgColors[status]} dark:border-gray-700`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Icon className={`w-5 h-5 ${statusColors[status]}`} />
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
            <p className={`text-lg font-semibold ${statusColors[status]}`}>
              {value}
              {unit}
            </p>
          </div>
        </div>
        {trend && (
          <div
            className={`flex items-center space-x-1 text-sm ${
              trend > 0
                ? "text-green-600"
                : trend < 0
                  ? "text-red-600"
                  : "text-gray-500"
            }`}
          >
            <TrendingUp
              className={`w-4 h-4 ${trend < 0 ? "rotate-180" : ""}`}
            />
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
    </div>
  );
};

const HealthIndicator = ({ label, healthy, description }) => (
  <div className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
    {healthy ? (
      <CheckCircle className="w-5 h-5 text-green-500" />
    ) : (
      <AlertTriangle className="w-5 h-5 text-red-500" />
    )}
    <div>
      <p
        className={`font-medium ${healthy ? "text-green-700 dark:text-green-400" : "text-red-700 dark:text-red-400"}`}
      >
        {label}
      </p>
      <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  </div>
);

export default function EmbeddingMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMetrics();
    // Refresh metrics every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const response = await analyticsAPI.getEmbeddingMetrics();
      if (response.success) {
        setMetrics(response.data);
        setError(null);
      } else {
        setError("Failed to fetch embedding metrics");
      }
    } catch (err) {
      setError(err.message || "Failed to fetch embedding metrics");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded mb-4 w-1/3"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-20 bg-gray-200 dark:bg-gray-700 rounded"
              ></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow">
        <div className="flex items-center space-x-2 text-red-600 dark:text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>Error loading embedding metrics: {error}</span>
        </div>
        <button
          onClick={fetchMetrics}
          className="mt-3 px-4 py-2 text-sm bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded hover:bg-red-200 dark:hover:bg-red-900/40"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow">
        <p className="text-gray-500 dark:text-gray-400">
          No embedding metrics available
        </p>
      </div>
    );
  }

  const { embedding_stats, health_indicators, performance_metrics } = metrics;

  return (
    <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
        Embedding Processing Metrics
      </h2>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard
          title="Total Batches"
          value={embedding_stats.total_batches_processed.toLocaleString()}
          icon={Database}
          status={
            embedding_stats.total_batches_processed > 0 ? "success" : "normal"
          }
        />
        <MetricCard
          title="Success Rate"
          value={Math.round(embedding_stats.success_rate * 100)}
          unit="%"
          icon={CheckCircle}
          status={
            embedding_stats.success_rate >= 0.95
              ? "success"
              : embedding_stats.success_rate >= 0.9
                ? "warning"
                : "error"
          }
        />
        <MetricCard
          title="Avg Processing Time"
          value={embedding_stats.average_processing_time_seconds}
          unit="s"
          icon={Clock}
          status={
            embedding_stats.average_processing_time_seconds <= 2
              ? "success"
              : embedding_stats.average_processing_time_seconds <= 5
                ? "warning"
                : "error"
          }
        />
        <MetricCard
          title="Queue Length"
          value={embedding_stats.current_queue_length}
          icon={Activity}
          status={
            embedding_stats.current_queue_length === 0
              ? "success"
              : embedding_stats.current_queue_length < 10
                ? "warning"
                : "error"
          }
        />
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <MetricCard
          title="Throughput"
          value={performance_metrics.throughput_batches_per_hour}
          unit=" batches/hr"
          icon={TrendingUp}
        />
        <MetricCard
          title="Token Rate"
          value={performance_metrics.tokens_per_second}
          unit=" tokens/s"
          icon={Zap}
        />
        <MetricCard
          title="Error Rate"
          value={performance_metrics.error_rate_percent}
          unit="%"
          icon={AlertTriangle}
          status={
            performance_metrics.error_rate_percent <= 1
              ? "success"
              : performance_metrics.error_rate_percent <= 5
                ? "warning"
                : "error"
          }
        />
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <MetricCard
          title="Total Tokens Processed"
          value={embedding_stats.total_tokens_processed.toLocaleString()}
          icon={Database}
        />
        <MetricCard
          title="Average Batch Size"
          value={embedding_stats.average_batch_size}
          unit=" texts"
          icon={Server}
        />
      </div>

      {/* Health Indicators */}
      <div className="space-y-3">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
          System Health
        </h3>
        <HealthIndicator
          label="Processing Health"
          healthy={health_indicators.processing_healthy}
          description={
            health_indicators.processing_healthy
              ? "Embedding processing is operating normally"
              : "Embedding processing has elevated error rates"
          }
        />
        <HealthIndicator
          label="Queue Health"
          healthy={health_indicators.queue_healthy}
          description={
            health_indicators.queue_healthy
              ? "Processing queue is at normal levels"
              : "Processing queue is experiencing backlog"
          }
        />
        <HealthIndicator
          label="Performance Health"
          healthy={health_indicators.performance_healthy}
          description={
            health_indicators.performance_healthy
              ? "Processing times are within acceptable limits"
              : "Processing times are elevated"
          }
        />
      </div>

      {/* Last Updated */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Last updated: {new Date().toLocaleString()}
        </p>
      </div>
    </div>
  );
}
