"""Comprehensive monitoring and analytics service."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import json
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.models.user import User
from app.models.project import Project
from app.models.code_document import CodeDocument
from app.models.chat_session import ChatSession, ChatMessage
from app.models.feedback import UserFeedback
from app.core.database import get_db

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""

    timestamp: datetime
    metric_name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsReport:
    """Analytics report structure."""

    report_id: str
    report_type: str
    generated_at: datetime
    time_range: Tuple[datetime, datetime]
    metrics: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and stores metrics data."""

    def __init__(self):
        self.metrics_buffer: List[MetricPoint] = []
        self.buffer_size = 1000
        self.flush_interval = 60  # seconds
        self.last_flush = time.time()

        # Real-time metrics
        self.realtime_metrics = defaultdict(list)
        self.metric_retention = 3600  # 1 hour for real-time metrics

    def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str] = None,
        metadata: Dict[str, Any] = None,
    ):
        """Record a metric point."""
        metric = MetricPoint(
            timestamp=datetime.utcnow(),
            metric_name=metric_name,
            value=value,
            labels=labels or {},
            metadata=metadata or {},
        )

        self.metrics_buffer.append(metric)

        # Also store in real-time buffer
        self.realtime_metrics[metric_name].append(metric)

        # Auto-flush if buffer is full
        if len(self.metrics_buffer) >= self.buffer_size:
            asyncio.create_task(self.flush_metrics())

    async def flush_metrics(self):
        """Flush metrics buffer to persistent storage."""
        if not self.metrics_buffer:
            return

        try:
            # In a real implementation, this would write to a time-series database
            # For now, we'll just log the metrics
            logger.info(f"Flushing {len(self.metrics_buffer)} metrics to storage")

            # Clear buffer
            self.metrics_buffer.clear()
            self.last_flush = time.time()

        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")

    def cleanup_realtime_metrics(self):
        """Clean up old real-time metrics."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.metric_retention)

        for metric_name in self.realtime_metrics:
            self.realtime_metrics[metric_name] = [
                metric
                for metric in self.realtime_metrics[metric_name]
                if metric.timestamp > cutoff_time
            ]

    def get_realtime_metrics(
        self, metric_names: List[str] = None, time_window: int = 300
    ) -> Dict[str, List[MetricPoint]]:
        """Get real-time metrics for specified time window."""
        self.cleanup_realtime_metrics()

        cutoff_time = datetime.utcnow() - timedelta(seconds=time_window)
        result = {}

        metrics_to_get = metric_names or list(self.realtime_metrics.keys())

        for metric_name in metrics_to_get:
            if metric_name in self.realtime_metrics:
                result[metric_name] = [
                    metric
                    for metric in self.realtime_metrics[metric_name]
                    if metric.timestamp > cutoff_time
                ]

        return result


class AnalyticsService:
    """Comprehensive analytics and monitoring service."""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.reports_cache = {}
        self.cache_ttl = 300  # 5 minutes

        # Performance tracking
        self.operation_times = defaultdict(list)
        self.error_counts = defaultdict(int)

        # User behavior tracking
        self.user_sessions = {}
        self.feature_usage = defaultdict(int)

    async def track_operation(
        self, operation_name: str, duration: float, success: bool = True
    ):
        """Track operation performance."""
        self.metrics_collector.record_metric(
            f"operation.{operation_name}.duration",
            duration,
            labels={"success": str(success)},
        )

        self.operation_times[operation_name].append(duration)

        if not success:
            self.error_counts[operation_name] += 1
            self.metrics_collector.record_metric(
                f"operation.{operation_name}.errors", 1
            )

    async def track_user_action(
        self, user_id: int, action: str, metadata: Dict[str, Any] = None
    ):
        """Track user actions and behavior."""
        self.metrics_collector.record_metric(
            "user.action",
            1,
            labels={"action": action, "user_id": str(user_id)},
            metadata=metadata,
        )

        self.feature_usage[action] += 1

        # Update user session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "start_time": datetime.utcnow(),
                "actions": [],
                "last_activity": datetime.utcnow(),
            }

        self.user_sessions[user_id]["actions"].append(
            {"action": action, "timestamp": datetime.utcnow(), "metadata": metadata}
        )
        self.user_sessions[user_id]["last_activity"] = datetime.utcnow()

    async def track_rag_performance(
        self,
        query: str,
        response_time: float,
        sources_count: int,
        confidence_score: float,
        user_id: int,
    ):
        """Track RAG system performance."""
        self.metrics_collector.record_metric("rag.response_time", response_time)
        self.metrics_collector.record_metric("rag.sources_count", sources_count)
        self.metrics_collector.record_metric("rag.confidence_score", confidence_score)

        # Track per-user RAG usage
        self.metrics_collector.record_metric(
            "rag.query",
            1,
            labels={"user_id": str(user_id)},
            metadata={"query_length": len(query)},
        )

    async def track_search_performance(
        self,
        query: str,
        search_type: str,
        results_count: int,
        response_time: float,
        user_id: int,
    ):
        """Track search performance and usage."""
        self.metrics_collector.record_metric(
            "search.response_time", response_time, labels={"search_type": search_type}
        )

        self.metrics_collector.record_metric(
            "search.results_count", results_count, labels={"search_type": search_type}
        )

        self.metrics_collector.record_metric(
            "search.query",
            1,
            labels={"search_type": search_type, "user_id": str(user_id)},
            metadata={"query_length": len(query)},
        )

    async def generate_performance_report(
        self, time_range: Tuple[datetime, datetime]
    ) -> AnalyticsReport:
        """Generate comprehensive performance report."""
        start_time, end_time = time_range

        try:
            # Get database session
            db = next(get_db())

            # Calculate performance metrics
            performance_metrics = await self._calculate_performance_metrics(
                db, start_time, end_time
            )

            # Calculate usage metrics
            usage_metrics = await self._calculate_usage_metrics(
                db, start_time, end_time
            )

            # Calculate quality metrics
            quality_metrics = await self._calculate_quality_metrics(
                db, start_time, end_time
            )

            # Generate insights
            insights = self._generate_performance_insights(
                performance_metrics, usage_metrics, quality_metrics
            )

            # Generate recommendations
            recommendations = self._generate_performance_recommendations(
                performance_metrics, usage_metrics
            )

            report = AnalyticsReport(
                report_id=f"perf_{int(time.time())}",
                report_type="performance",
                generated_at=datetime.utcnow(),
                time_range=time_range,
                metrics={
                    "performance": performance_metrics,
                    "usage": usage_metrics,
                    "quality": quality_metrics,
                },
                insights=insights,
                recommendations=recommendations,
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            raise

    async def _calculate_performance_metrics(
        self, db: Session, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate performance-related metrics."""
        # Query response times
        avg_response_times = {}
        for operation in self.operation_times:
            times = self.operation_times[operation]
            if times:
                avg_response_times[operation] = {
                    "avg": statistics.mean(times),
                    "median": statistics.median(times),
                    "p95": (
                        statistics.quantiles(times, n=20)[18]
                        if len(times) > 10
                        else max(times)
                    ),
                    "count": len(times),
                }

        # Error rates
        error_rates = {}
        for operation, error_count in self.error_counts.items():
            total_operations = len(
                self.operation_times.get(operation, [1])
            )  # Avoid division by zero
            error_rates[operation] = (
                error_count / total_operations if total_operations > 0 else 0
            )

        # Database performance
        db_metrics = await self._get_database_metrics(db, start_time, end_time)

        return {
            "response_times": avg_response_times,
            "error_rates": error_rates,
            "database": db_metrics,
            "system_load": self._get_system_metrics(),
        }

    async def _calculate_usage_metrics(
        self, db: Session, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate usage-related metrics."""
        # Active users
        active_users = (
            db.query(func.count(func.distinct(ChatMessage.user_id)))
            .filter(ChatMessage.created_at.between(start_time, end_time))
            .scalar()
            or 0
        )

        # Total sessions
        total_sessions = (
            db.query(func.count(ChatSession.id))
            .filter(ChatSession.created_at.between(start_time, end_time))
            .scalar()
            or 0
        )

        # Messages per user
        avg_messages = (
            db.query(func.avg(func.count(ChatMessage.id)))
            .filter(ChatMessage.created_at.between(start_time, end_time))
            .group_by(ChatMessage.user_id)
            .scalar()
            or 0
        )

        # Document interactions
        document_views = (
            db.query(func.count(CodeDocument.id))
            .filter(CodeDocument.updated_at.between(start_time, end_time))
            .scalar()
            or 0
        )

        # Feature usage
        feature_usage_metrics = dict(self.feature_usage)

        # User session metrics
        session_durations = []
        for user_id, session in self.user_sessions.items():
            if start_time <= session["start_time"] <= end_time:
                duration = (
                    session["last_activity"] - session["start_time"]
                ).total_seconds()
                session_durations.append(duration)

        avg_session_duration = (
            statistics.mean(session_durations) if session_durations else 0
        )

        return {
            "active_users": active_users,
            "total_sessions": total_sessions,
            "avg_messages_per_user": float(avg_messages),
            "document_views": document_views,
            "feature_usage": feature_usage_metrics,
            "avg_session_duration": avg_session_duration,
            "session_count": len(session_durations),
        }

    async def _calculate_quality_metrics(
        self, db: Session, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate quality-related metrics."""
        # User feedback metrics
        feedback_query = db.query(UserFeedback).filter(
            UserFeedback.created_at.between(start_time, end_time)
        )

        feedback_count = feedback_query.count()

        if feedback_count > 0:
            avg_rating = (
                db.query(func.avg(UserFeedback.rating))
                .filter(UserFeedback.created_at.between(start_time, end_time))
                .scalar()
                or 0
            )

            helpful_percentage = (
                db.query(
                    func.count(UserFeedback.id).filter(UserFeedback.helpful == True)
                )
                .filter(UserFeedback.created_at.between(start_time, end_time))
                .scalar()
                / feedback_count
                * 100
            )

            # Quality ratings breakdown
            accuracy_rating = (
                db.query(func.avg(UserFeedback.accuracy_rating))
                .filter(
                    UserFeedback.created_at.between(start_time, end_time),
                    UserFeedback.accuracy_rating.isnot(None),
                )
                .scalar()
                or 0
            )

            clarity_rating = (
                db.query(func.avg(UserFeedback.clarity_rating))
                .filter(
                    UserFeedback.created_at.between(start_time, end_time),
                    UserFeedback.clarity_rating.isnot(None),
                )
                .scalar()
                or 0
            )

            completeness_rating = (
                db.query(func.avg(UserFeedback.completeness_rating))
                .filter(
                    UserFeedback.created_at.between(start_time, end_time),
                    UserFeedback.completeness_rating.isnot(None),
                )
                .scalar()
                or 0
            )
        else:
            avg_rating = 0
            helpful_percentage = 0
            accuracy_rating = 0
            clarity_rating = 0
            completeness_rating = 0

        # Content quality (based on real-time metrics)
        rag_metrics = self.metrics_collector.get_realtime_metrics(
            ["rag.confidence_score", "rag.sources_count"]
        )

        avg_confidence = 0
        avg_sources = 0

        if "rag.confidence_score" in rag_metrics:
            confidence_scores = [m.value for m in rag_metrics["rag.confidence_score"]]
            avg_confidence = (
                statistics.mean(confidence_scores) if confidence_scores else 0
            )

        if "rag.sources_count" in rag_metrics:
            source_counts = [m.value for m in rag_metrics["rag.sources_count"]]
            avg_sources = statistics.mean(source_counts) if source_counts else 0

        return {
            "user_feedback": {
                "total_feedback": feedback_count,
                "avg_rating": float(avg_rating),
                "helpful_percentage": float(helpful_percentage),
                "accuracy_rating": float(accuracy_rating),
                "clarity_rating": float(clarity_rating),
                "completeness_rating": float(completeness_rating),
            },
            "content_quality": {
                "avg_confidence_score": avg_confidence,
                "avg_sources_per_response": avg_sources,
            },
        }

    async def _get_database_metrics(
        self, db: Session, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Get database performance metrics."""
        try:
            # Simple database metrics
            total_documents = db.query(func.count(CodeDocument.id)).scalar() or 0
            total_users = db.query(func.count(User.id)).scalar() or 0
            total_projects = db.query(func.count(Project.id)).scalar() or 0

            # Recent activity
            recent_messages = (
                db.query(func.count(ChatMessage.id))
                .filter(ChatMessage.created_at.between(start_time, end_time))
                .scalar()
                or 0
            )

            return {
                "total_documents": total_documents,
                "total_users": total_users,
                "total_projects": total_projects,
                "recent_messages": recent_messages,
                "storage_size_mb": total_documents * 0.1,  # Rough estimate
            }

        except Exception as e:
            logger.error(f"Failed to get database metrics: {e}")
            return {}

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        import psutil
        import os

        try:
            # Get actual system metrics using psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Network I/O (if available)
            try:
                net_io = psutil.net_io_counters()
                network_bytes_sent = net_io.bytes_sent if net_io else 0
                network_bytes_recv = net_io.bytes_recv if net_io else 0
            except Exception:
                network_bytes_sent = 0
                network_bytes_recv = 0

            return {
                "cpu_usage": round(cpu_percent, 1),
                "memory_usage": round(memory.percent, 1),
                "memory_available_mb": round(memory.available / (1024 * 1024), 1),
                "disk_usage": round((disk.used / disk.total) * 100, 1),
                "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 1),
                "network_bytes_sent": network_bytes_sent,
                "network_bytes_recv": network_bytes_recv,
                "load_average": (
                    os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
                ),
                "process_count": len(psutil.pids()),
            }

        except ImportError:
            # Fallback if psutil is not available
            logger.warning("psutil not available, using fallback system metrics")
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "network_io": 0.0,
                "status": "metrics_unavailable",
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "network_io": 0.0,
                "error": str(e),
            }

    def _generate_performance_insights(
        self,
        performance_metrics: Dict[str, Any],
        usage_metrics: Dict[str, Any],
        quality_metrics: Dict[str, Any],
    ) -> List[str]:
        """Generate insights from performance data."""
        insights = []

        # Performance insights
        response_times = performance_metrics.get("response_times", {})
        for operation, metrics in response_times.items():
            if metrics["avg"] > 2.0:  # > 2 seconds
                insights.append(
                    f"High response time detected for {operation}: {metrics['avg']:.2f}s average"
                )

        # Error rate insights
        error_rates = performance_metrics.get("error_rates", {})
        for operation, rate in error_rates.items():
            if rate > 0.05:  # > 5% error rate
                insights.append(f"High error rate for {operation}: {rate*100:.1f}%")

        # Usage insights
        active_users = usage_metrics.get("active_users", 0)
        if active_users > 100:
            insights.append(f"High user activity: {active_users} active users")
        elif active_users < 10:
            insights.append(f"Low user engagement: only {active_users} active users")

        # Quality insights
        user_feedback = quality_metrics.get("user_feedback", {})
        avg_rating = user_feedback.get("avg_rating", 0)
        if avg_rating > 4.0:
            insights.append(
                f"Excellent user satisfaction: {avg_rating:.1f}/5.0 average rating"
            )
        elif avg_rating < 3.0:
            insights.append(
                f"User satisfaction needs improvement: {avg_rating:.1f}/5.0 average rating"
            )

        confidence_score = quality_metrics.get("content_quality", {}).get(
            "avg_confidence_score", 0
        )
        if confidence_score < 0.7:
            insights.append(
                f"RAG confidence may need improvement: {confidence_score:.2f} average confidence"
            )

        return insights

    def _generate_performance_recommendations(
        self, performance_metrics: Dict[str, Any], usage_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for performance improvement."""
        recommendations = []

        # Performance recommendations
        response_times = performance_metrics.get("response_times", {})
        for operation, metrics in response_times.items():
            if metrics["avg"] > 2.0:
                recommendations.append(
                    f"Consider optimizing {operation} - current avg: {metrics['avg']:.2f}s"
                )

        # Caching recommendations
        if any(metrics["avg"] > 1.0 for metrics in response_times.values()):
            recommendations.append(
                "Implement or improve caching for frequently accessed data"
            )

        # Scaling recommendations
        active_users = usage_metrics.get("active_users", 0)
        if active_users > 100:
            recommendations.append("Consider horizontal scaling due to high user load")

        # Database recommendations
        db_metrics = performance_metrics.get("database", {})
        total_documents = db_metrics.get("total_documents", 0)
        if total_documents > 10000:
            recommendations.append(
                "Consider database optimization or partitioning for large document set"
            )

        return recommendations

    async def get_realtime_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time data for monitoring dashboard."""
        try:
            # Get recent metrics
            realtime_metrics = self.metrics_collector.get_realtime_metrics(
                time_window=300  # Last 5 minutes
            )

            # Calculate current rates
            current_rates = {}
            for metric_name, metrics in realtime_metrics.items():
                if metrics:
                    # Calculate rate per minute
                    time_span = 300 / 60  # 5 minutes
                    current_rates[metric_name] = len(metrics) / time_span

            # System status
            error_count = sum(self.error_counts.values())
            total_operations = sum(
                len(times) for times in self.operation_times.values()
            )
            overall_error_rate = (
                error_count / total_operations if total_operations > 0 else 0
            )

            # User activity
            active_sessions = len(
                [
                    session
                    for session in self.user_sessions.values()
                    if (datetime.utcnow() - session["last_activity"]).total_seconds()
                    < 300
                ]
            )

            return {
                "timestamp": datetime.utcnow(),
                "system_status": "healthy" if overall_error_rate < 0.05 else "degraded",
                "active_sessions": active_sessions,
                "current_rates": current_rates,
                "recent_metrics": {
                    name: len(metrics) for name, metrics in realtime_metrics.items()
                },
                "error_rate": overall_error_rate,
                "top_features": dict(Counter(self.feature_usage).most_common(10)),
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {"error": str(e)}

    async def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old analytics data."""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Clean up operation times
        for operation in list(self.operation_times.keys()):
            # Keep only recent data (simplified cleanup)
            if len(self.operation_times[operation]) > 1000:
                self.operation_times[operation] = self.operation_times[operation][-500:]

        # Clean up user sessions
        expired_sessions = [
            user_id
            for user_id, session in self.user_sessions.items()
            if session["start_time"] < cutoff_date
        ]

        for user_id in expired_sessions:
            del self.user_sessions[user_id]

        # Clean up metrics collector
        self.metrics_collector.cleanup_realtime_metrics()

        logger.info(f"Cleaned up analytics data older than {retention_days} days")


# Global analytics service instance
analytics_service = AnalyticsService()
