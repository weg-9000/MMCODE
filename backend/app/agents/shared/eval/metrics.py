"""
Evaluation Metrics
==================

Metrics collection and analysis for agent evaluation.
Supports the Open Coding pattern analysis approach.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict
import statistics

from .evaluator import EvalResult, EvalCategory, Severity


@dataclass
class ResponseMetrics:
    """Metrics for a single response"""
    response_time_ms: float = 0.0
    token_count: int = 0
    response_size_bytes: int = 0
    quality_score: float = 0.0


@dataclass
class QualityMetrics:
    """Aggregated quality metrics"""

    # Counts
    total_evaluations: int = 0
    passed_count: int = 0
    failed_count: int = 0

    # Scores
    average_score: float = 0.0
    min_score: float = 1.0
    max_score: float = 0.0
    score_std_dev: float = 0.0

    # Response Time
    average_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Issue Distribution
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    issues_by_severity: Dict[str, int] = field(default_factory=dict)

    # Time Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "pass_rate": self.passed_count / self.total_evaluations if self.total_evaluations > 0 else 0,
            "average_score": round(self.average_score, 3),
            "min_score": round(self.min_score, 3),
            "max_score": round(self.max_score, 3),
            "score_std_dev": round(self.score_std_dev, 3),
            "average_response_time_ms": round(self.average_response_time_ms, 1),
            "p50_response_time_ms": round(self.p50_response_time_ms, 1),
            "p95_response_time_ms": round(self.p95_response_time_ms, 1),
            "p99_response_time_ms": round(self.p99_response_time_ms, 1),
            "issues_by_category": self.issues_by_category,
            "issues_by_severity": self.issues_by_severity,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


class MetricsCollector:
    """
    Collects and aggregates evaluation metrics

    Implements Step 2 of the methodology: Pattern Categorization
    through statistical analysis of evaluation results.
    """

    def __init__(self):
        self.results: List[EvalResult] = []
        self._scores: List[float] = []
        self._response_times: List[float] = []

    def add_result(self, result: EvalResult):
        """Add an evaluation result"""
        self.results.append(result)
        self._scores.append(result.score)
        self._response_times.append(result.response_time_ms)

    def add_results(self, results: List[EvalResult]):
        """Add multiple evaluation results"""
        for result in results:
            self.add_result(result)

    def get_quality_metrics(self) -> QualityMetrics:
        """Calculate aggregated quality metrics"""
        if not self.results:
            return QualityMetrics()

        metrics = QualityMetrics(
            total_evaluations=len(self.results),
            passed_count=sum(1 for r in self.results if r.passed),
            failed_count=sum(1 for r in self.results if not r.passed),
            average_score=statistics.mean(self._scores),
            min_score=min(self._scores),
            max_score=max(self._scores),
        )

        # Standard deviation
        if len(self._scores) > 1:
            metrics.score_std_dev = statistics.stdev(self._scores)

        # Response time percentiles
        if self._response_times:
            sorted_times = sorted(self._response_times)
            metrics.average_response_time_ms = statistics.mean(self._response_times)
            metrics.p50_response_time_ms = self._percentile(sorted_times, 50)
            metrics.p95_response_time_ms = self._percentile(sorted_times, 95)
            metrics.p99_response_time_ms = self._percentile(sorted_times, 99)

        # Issue distribution
        metrics.issues_by_category = self._count_issues_by_category()
        metrics.issues_by_severity = self._count_issues_by_severity()

        # Time period
        timestamps = [r.timestamp for r in self.results if r.timestamp]
        if timestamps:
            metrics.period_start = min(timestamps)
            metrics.period_end = max(timestamps)

        return metrics

    def get_metrics_by_agent(self) -> Dict[str, QualityMetrics]:
        """Get metrics grouped by agent"""
        agents = set(r.agent_id for r in self.results)
        result = {}

        for agent_id in agents:
            collector = MetricsCollector()
            for r in self.results:
                if r.agent_id == agent_id:
                    collector.add_result(r)
            result[agent_id] = collector.get_quality_metrics()

        return result

    def get_metrics_by_task_type(self) -> Dict[str, QualityMetrics]:
        """Get metrics grouped by task type"""
        task_types = set(r.task_type for r in self.results)
        result = {}

        for task_type in task_types:
            collector = MetricsCollector()
            for r in self.results:
                if r.task_type == task_type:
                    collector.add_result(r)
            result[task_type] = collector.get_quality_metrics()

        return result

    def get_top_issues(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequent issues (Step 2: Find patterns)

        This is the core of the Open Coding → Categorization process.
        """
        issue_counts = defaultdict(int)
        issue_examples = defaultdict(list)

        for result in self.results:
            for issue in result.issues:
                key = (issue.category.value, issue.severity.value)
                issue_counts[key] += 1
                if len(issue_examples[key]) < 3:  # Keep up to 3 examples
                    issue_examples[key].append({
                        "description": issue.description,
                        "evidence": issue.evidence,
                        "agent_id": result.agent_id,
                        "task_type": result.task_type
                    })

        # Sort by count (most frequent first)
        sorted_issues = sorted(
            issue_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {
                "category": category,
                "severity": severity,
                "count": count,
                "percentage": count / len(self.results) * 100 if self.results else 0,
                "examples": issue_examples[(category, severity)]
            }
            for (category, severity), count in sorted_issues
        ]

    def get_trend_analysis(self, window_size: int = 10) -> List[Dict[str, Any]]:
        """
        Analyze score trends over time

        Useful for detecting regressions.
        """
        if len(self.results) < window_size:
            return []

        # Sort by timestamp
        sorted_results = sorted(self.results, key=lambda x: x.timestamp)

        trends = []
        for i in range(window_size, len(sorted_results) + 1):
            window = sorted_results[i-window_size:i]
            avg_score = statistics.mean(r.score for r in window)
            pass_rate = sum(1 for r in window if r.passed) / len(window)

            trends.append({
                "window_end": window[-1].timestamp.isoformat(),
                "average_score": round(avg_score, 3),
                "pass_rate": round(pass_rate, 3),
                "samples": len(window)
            })

        return trends

    def detect_regressions(self, threshold: float = 0.1) -> List[Dict[str, Any]]:
        """
        Detect quality regressions

        Compares recent performance to historical baseline.
        """
        if len(self.results) < 20:
            return []

        sorted_results = sorted(self.results, key=lambda x: x.timestamp)

        # Split into old (baseline) and recent
        split_point = len(sorted_results) // 2
        baseline = sorted_results[:split_point]
        recent = sorted_results[split_point:]

        baseline_avg = statistics.mean(r.score for r in baseline)
        recent_avg = statistics.mean(r.score for r in recent)

        regressions = []

        # Overall regression
        if baseline_avg - recent_avg > threshold:
            regressions.append({
                "type": "overall",
                "baseline_score": round(baseline_avg, 3),
                "recent_score": round(recent_avg, 3),
                "delta": round(recent_avg - baseline_avg, 3),
                "severity": "high" if baseline_avg - recent_avg > 0.2 else "medium"
            })

        # Per-agent regression
        agents = set(r.agent_id for r in self.results)
        for agent_id in agents:
            agent_baseline = [r.score for r in baseline if r.agent_id == agent_id]
            agent_recent = [r.score for r in recent if r.agent_id == agent_id]

            if agent_baseline and agent_recent:
                bl_avg = statistics.mean(agent_baseline)
                rc_avg = statistics.mean(agent_recent)

                if bl_avg - rc_avg > threshold:
                    regressions.append({
                        "type": "agent",
                        "agent_id": agent_id,
                        "baseline_score": round(bl_avg, 3),
                        "recent_score": round(rc_avg, 3),
                        "delta": round(rc_avg - bl_avg, 3)
                    })

        return regressions

    def _percentile(self, sorted_data: List[float], p: int) -> float:
        """Calculate percentile"""
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)

    def _count_issues_by_category(self) -> Dict[str, int]:
        """Count issues by category"""
        counts = defaultdict(int)
        for result in self.results:
            for issue in result.issues:
                counts[issue.category.value] += 1
        return dict(counts)

    def _count_issues_by_severity(self) -> Dict[str, int]:
        """Count issues by severity"""
        counts = defaultdict(int)
        for result in self.results:
            for issue in result.issues:
                counts[issue.severity.value] += 1
        return dict(counts)


def create_pivot_table(
    results: List[EvalResult],
    row_key: str = "agent_id",
    col_key: str = "task_type"
) -> Dict[str, Dict[str, Any]]:
    """
    Create a pivot table from results (Step 2: Categorization)

    Args:
        results: List of evaluation results
        row_key: Field to use for rows (agent_id, task_type)
        col_key: Field to use for columns

    Returns:
        Nested dict with aggregated metrics
    """
    pivot = defaultdict(lambda: defaultdict(list))

    for result in results:
        row = getattr(result, row_key, "unknown")
        col = getattr(result, col_key, "unknown")
        pivot[row][col].append(result.score)

    # Aggregate
    aggregated = {}
    for row, cols in pivot.items():
        aggregated[row] = {}
        for col, scores in cols.items():
            aggregated[row][col] = {
                "count": len(scores),
                "avg_score": round(statistics.mean(scores), 3) if scores else 0,
                "min_score": round(min(scores), 3) if scores else 0,
                "max_score": round(max(scores), 3) if scores else 0
            }

    return aggregated
