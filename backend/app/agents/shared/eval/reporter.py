"""
Evaluation Reporter
===================

Generates reports from evaluation results.
Supports multiple output formats for analysis.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .evaluator import EvalResult, EvalCategory, Severity
from .metrics import MetricsCollector, QualityMetrics, create_pivot_table
from .test_cases import TestCaseResult


@dataclass
class EvalReport:
    """Complete evaluation report"""

    # Identification
    report_id: str
    title: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Summary
    total_evaluations: int = 0
    pass_rate: float = 0.0
    average_score: float = 0.0

    # Metrics
    quality_metrics: Optional[QualityMetrics] = None
    metrics_by_agent: Dict[str, QualityMetrics] = field(default_factory=dict)
    metrics_by_task: Dict[str, QualityMetrics] = field(default_factory=dict)

    # Issues
    top_issues: List[Dict[str, Any]] = field(default_factory=list)
    regressions: List[Dict[str, Any]] = field(default_factory=list)

    # Raw data
    results: List[EvalResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_evaluations": self.total_evaluations,
                "pass_rate": round(self.pass_rate, 3),
                "average_score": round(self.average_score, 3)
            },
            "quality_metrics": self.quality_metrics.to_dict() if self.quality_metrics else None,
            "metrics_by_agent": {
                k: v.to_dict() for k, v in self.metrics_by_agent.items()
            },
            "metrics_by_task": {
                k: v.to_dict() for k, v in self.metrics_by_task.items()
            },
            "top_issues": self.top_issues,
            "regressions": self.regressions
        }


class EvalReporter:
    """
    Generates evaluation reports

    Implements Step 3 methodology: Clear decision-making output
    for the Benevolent Dictator to review.
    """

    def __init__(self, title: str = "Agent Evaluation Report"):
        self.title = title
        self.results: List[EvalResult] = []
        self.test_case_results: List[TestCaseResult] = []

    def add_result(self, result: EvalResult):
        """Add an evaluation result"""
        self.results.append(result)

    def add_results(self, results: List[EvalResult]):
        """Add multiple evaluation results"""
        self.results.extend(results)

    def add_test_case_results(self, results: List[TestCaseResult]):
        """Add test case results"""
        self.test_case_results.extend(results)
        for tcr in results:
            self.results.append(tcr.eval_result)

    def generate_report(self) -> EvalReport:
        """Generate complete evaluation report"""
        import uuid

        collector = MetricsCollector()
        collector.add_results(self.results)

        quality_metrics = collector.get_quality_metrics()

        report = EvalReport(
            report_id=str(uuid.uuid4())[:8],
            title=self.title,
            total_evaluations=len(self.results),
            pass_rate=quality_metrics.passed_count / len(self.results) if self.results else 0,
            average_score=quality_metrics.average_score,
            quality_metrics=quality_metrics,
            metrics_by_agent=collector.get_metrics_by_agent(),
            metrics_by_task=collector.get_metrics_by_task_type(),
            top_issues=collector.get_top_issues(10),
            regressions=collector.detect_regressions(),
            results=self.results
        )

        return report

    def generate_markdown_report(self) -> str:
        """Generate Markdown formatted report"""
        report = self.generate_report()

        md = []
        md.append(f"# {report.title}")
        md.append(f"\n**Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append(f"\n**Report ID**: {report.report_id}\n")

        # Executive Summary
        md.append("## Executive Summary\n")
        md.append(f"| Metric | Value |")
        md.append(f"|--------|-------|")
        md.append(f"| Total Evaluations | {report.total_evaluations} |")
        md.append(f"| Pass Rate | {report.pass_rate:.1%} |")
        md.append(f"| Average Score | {report.average_score:.2f} |")
        md.append("")

        # Pass/Fail Status
        status_emoji = "✅" if report.pass_rate >= 0.8 else "⚠️" if report.pass_rate >= 0.6 else "❌"
        md.append(f"**Overall Status**: {status_emoji} {'PASSING' if report.pass_rate >= 0.7 else 'NEEDS ATTENTION'}\n")

        # Metrics by Agent
        if report.metrics_by_agent:
            md.append("## Metrics by Agent\n")
            md.append("| Agent | Evaluations | Pass Rate | Avg Score | Avg Response Time |")
            md.append("|-------|-------------|-----------|-----------|-------------------|")
            for agent_id, metrics in report.metrics_by_agent.items():
                pass_rate = metrics.passed_count / metrics.total_evaluations if metrics.total_evaluations > 0 else 0
                md.append(f"| {agent_id} | {metrics.total_evaluations} | {pass_rate:.1%} | {metrics.average_score:.2f} | {metrics.average_response_time_ms:.0f}ms |")
            md.append("")

        # Metrics by Task Type
        if report.metrics_by_task:
            md.append("## Metrics by Task Type\n")
            md.append("| Task Type | Evaluations | Pass Rate | Avg Score |")
            md.append("|-----------|-------------|-----------|-----------|")
            for task_type, metrics in report.metrics_by_task.items():
                pass_rate = metrics.passed_count / metrics.total_evaluations if metrics.total_evaluations > 0 else 0
                md.append(f"| {task_type} | {metrics.total_evaluations} | {pass_rate:.1%} | {metrics.average_score:.2f} |")
            md.append("")

        # Top Issues (Key insight from Open Coding)
        if report.top_issues:
            md.append("## Top Issues (Priority Order)\n")
            md.append("These are the most frequent issues found during evaluation:\n")

            for i, issue in enumerate(report.top_issues[:5], 1):
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(issue["severity"], "⚪")

                md.append(f"### {i}. {issue['category']} {severity_emoji}")
                md.append(f"- **Severity**: {issue['severity'].upper()}")
                md.append(f"- **Occurrences**: {issue['count']} ({issue['percentage']:.1f}%)")

                if issue.get("examples"):
                    md.append(f"- **Examples**:")
                    for ex in issue["examples"][:2]:
                        md.append(f"  - {ex['description'][:100]}...")
                md.append("")

        # Regressions
        if report.regressions:
            md.append("## ⚠️ Detected Regressions\n")
            for reg in report.regressions:
                if reg["type"] == "overall":
                    md.append(f"- **Overall Quality Regression**: Score dropped from {reg['baseline_score']:.2f} to {reg['recent_score']:.2f} (Δ{reg['delta']:.2f})")
                else:
                    md.append(f"- **{reg['agent_id']}**: Score dropped from {reg['baseline_score']:.2f} to {reg['recent_score']:.2f}")
            md.append("")

        # Issue Distribution
        if report.quality_metrics:
            md.append("## Issue Distribution\n")

            if report.quality_metrics.issues_by_severity:
                md.append("### By Severity")
                md.append("| Severity | Count |")
                md.append("|----------|-------|")
                for sev, count in sorted(report.quality_metrics.issues_by_severity.items()):
                    md.append(f"| {sev} | {count} |")
                md.append("")

            if report.quality_metrics.issues_by_category:
                md.append("### By Category")
                md.append("| Category | Count |")
                md.append("|----------|-------|")
                sorted_cats = sorted(
                    report.quality_metrics.issues_by_category.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                for cat, count in sorted_cats[:10]:
                    md.append(f"| {cat} | {count} |")
                md.append("")

        # Recommendations (Benevolent Dictator guidance)
        md.append("## Recommendations\n")

        recommendations = self._generate_recommendations(report)
        for i, rec in enumerate(recommendations, 1):
            md.append(f"{i}. {rec}")
        md.append("")

        # Test Case Summary (if available)
        if self.test_case_results:
            md.append("## Test Case Results\n")
            passed = sum(1 for r in self.test_case_results if r.passed)
            failed = len(self.test_case_results) - passed

            md.append(f"- **Passed**: {passed}")
            md.append(f"- **Failed**: {failed}")
            md.append(f"- **Pass Rate**: {passed/len(self.test_case_results):.1%}")
            md.append("")

            if failed > 0:
                md.append("### Failed Tests")
                for tcr in self.test_case_results:
                    if not tcr.passed:
                        md.append(f"- **{tcr.test_case.test_id}**: {tcr.test_case.name}")
                        md.append(f"  - Reason: {tcr.failure_reason}")
                md.append("")

        return "\n".join(md)

    def generate_json_report(self) -> str:
        """Generate JSON formatted report"""
        report = self.generate_report()
        return json.dumps(report.to_dict(), indent=2, default=str)

    def _generate_recommendations(self, report: EvalReport) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []

        # Based on pass rate
        if report.pass_rate < 0.7:
            recommendations.append(
                "**Critical**: Pass rate is below 70%. Focus on fixing CRITICAL and HIGH severity issues first."
            )
        elif report.pass_rate < 0.9:
            recommendations.append(
                "Pass rate is acceptable but below 90%. Review HIGH severity issues to improve quality."
            )

        # Based on top issues
        if report.top_issues:
            top_issue = report.top_issues[0]
            if top_issue["severity"] == "critical":
                recommendations.append(
                    f"**Immediate Action**: Address '{top_issue['category']}' issues occurring in {top_issue['percentage']:.0f}% of evaluations."
                )

            # Check for format errors
            format_issues = [i for i in report.top_issues if i["category"] == "format_error"]
            if format_issues:
                recommendations.append(
                    "Review agent output schema validation - format errors indicate structural issues."
                )

            # Check for hallucinations
            hallucination_issues = [i for i in report.top_issues if i["category"] == "hallucination"]
            if hallucination_issues:
                recommendations.append(
                    "Implement fact-checking mechanisms to reduce hallucination issues."
                )

        # Based on response time
        if report.quality_metrics and report.quality_metrics.p95_response_time_ms > 10000:
            recommendations.append(
                f"Response time P95 is {report.quality_metrics.p95_response_time_ms:.0f}ms. Consider optimization or caching."
            )

        # Based on regressions
        if report.regressions:
            recommendations.append(
                "Quality regressions detected. Review recent changes and consider rollback if necessary."
            )

        # Default recommendation
        if not recommendations:
            recommendations.append(
                "Quality metrics look good. Continue monitoring and add more test cases for edge cases."
            )

        return recommendations

    def export_to_file(self, filepath: str, format: str = "markdown"):
        """Export report to file"""
        if format == "markdown":
            content = self.generate_markdown_report()
        elif format == "json":
            content = self.generate_json_report()
        else:
            raise ValueError(f"Unsupported format: {format}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
