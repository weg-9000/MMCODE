"""
Evaluation Pipeline
===================

Automated evaluation pipeline for running agent tests and generating reports.
Implements continuous quality monitoring based on the 3-step methodology.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from .evaluator import AgentEvaluator, EvalResult, EvalCategory, Severity
from .test_cases import (
    TestCaseRunner,
    TestCaseResult,
    get_all_test_cases,
    get_architect_agent_test_cases,
    get_stack_recommender_test_cases,
    get_document_agent_test_cases
)
from .metrics import MetricsCollector, QualityMetrics
from .reporter import EvalReporter


@dataclass
class PipelineConfig:
    """Configuration for the eval pipeline"""

    # Test Selection
    include_agents: Optional[List[str]] = None  # None = all agents
    include_categories: Optional[List[str]] = None  # None = all categories
    include_tags: Optional[List[str]] = None  # None = all tags

    # Execution
    parallel_execution: bool = False
    timeout_seconds: float = 300.0
    retry_count: int = 1

    # Thresholds
    min_pass_rate: float = 0.7
    min_average_score: float = 0.7
    fail_on_critical: bool = True

    # Output
    output_dir: str = "./eval_results"
    generate_markdown: bool = True
    generate_json: bool = True
    save_individual_results: bool = False

    # Notifications (for CI/CD integration)
    notify_on_failure: bool = False
    slack_webhook: Optional[str] = None


@dataclass
class PipelineResult:
    """Result of a pipeline run"""

    # Summary
    run_id: str
    timestamp: datetime
    duration_seconds: float

    # Results
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    pass_rate: float = 0.0
    average_score: float = 0.0

    # Status
    pipeline_passed: bool = False
    failure_reasons: List[str] = field(default_factory=list)

    # Detailed Results
    test_results: List[TestCaseResult] = field(default_factory=list)
    quality_metrics: Optional[QualityMetrics] = None

    # Output Files
    markdown_report_path: Optional[str] = None
    json_report_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "pass_rate": round(self.pass_rate, 3),
                "average_score": round(self.average_score, 3)
            },
            "pipeline_passed": self.pipeline_passed,
            "failure_reasons": self.failure_reasons,
            "files": {
                "markdown_report": self.markdown_report_path,
                "json_report": self.json_report_path
            }
        }


class EvalPipeline:
    """
    Automated evaluation pipeline

    Usage:
        pipeline = EvalPipeline(config)
        result = await pipeline.run(agent_executors)

        # Or with mock agents for testing
        result = await pipeline.run_with_mock_agents()
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger("EvalPipeline")
        self.runner = TestCaseRunner()

    def _load_test_cases(self):
        """Load test cases based on configuration"""
        # Get all test cases
        all_cases = get_all_test_cases()

        # Filter by agent
        if self.config.include_agents:
            all_cases = [
                tc for tc in all_cases
                if tc.agent_id in self.config.include_agents
            ]

        # Filter by tags
        if self.config.include_tags:
            all_cases = [
                tc for tc in all_cases
                if any(tag in tc.tags for tag in self.config.include_tags)
            ]

        self.runner.add_test_cases(all_cases)
        self.logger.info(f"Loaded {len(all_cases)} test cases")

    async def run(
        self,
        agent_executors: Dict[str, Callable]
    ) -> PipelineResult:
        """
        Run the evaluation pipeline

        Args:
            agent_executors: Dict mapping agent_id to async executor function
                            Executor signature: async def(task_type, context) -> response

        Returns:
            PipelineResult with complete evaluation data
        """
        import uuid

        run_id = str(uuid.uuid4())[:8]
        start_time = datetime.now(timezone.utc)

        self.logger.info(f"Starting eval pipeline run: {run_id}")

        # Load test cases
        self._load_test_cases()

        # Create unified executor
        async def unified_executor(task_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
            # Determine which agent to use based on task_type
            agent_mapping = {
                "architecture_design": "architect-agent",
                "pattern_recommendation": "architect-agent",
                "stack_recommendation": "stack-recommender-agent",
                "technology_evaluation": "stack-recommender-agent",
                "documentation_generation": "document-agent",
                "api_documentation": "document-agent",
            }

            agent_id = agent_mapping.get(task_type)
            if agent_id and agent_id in agent_executors:
                return await agent_executors[agent_id](task_type, context)

            # Fallback: try first available executor
            for executor in agent_executors.values():
                return await executor(task_type, context)

            raise ValueError(f"No executor found for task_type: {task_type}")

        # Run tests
        try:
            test_results = await asyncio.wait_for(
                self.runner.run_all(
                    unified_executor,
                    parallel=self.config.parallel_execution
                ),
                timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Pipeline timed out after {self.config.timeout_seconds}s")
            return PipelineResult(
                run_id=run_id,
                timestamp=start_time,
                duration_seconds=self.config.timeout_seconds,
                pipeline_passed=False,
                failure_reasons=["Pipeline execution timed out"]
            )

        # Calculate metrics
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        passed = sum(1 for r in test_results if r.passed)
        failed = len(test_results) - passed
        pass_rate = passed / len(test_results) if test_results else 0
        avg_score = sum(r.eval_result.score for r in test_results) / len(test_results) if test_results else 0

        # Collect quality metrics
        collector = MetricsCollector()
        collector.add_results([r.eval_result for r in test_results])
        quality_metrics = collector.get_quality_metrics()

        # Determine pipeline pass/fail
        failure_reasons = []
        pipeline_passed = True

        if pass_rate < self.config.min_pass_rate:
            pipeline_passed = False
            failure_reasons.append(
                f"Pass rate {pass_rate:.1%} below threshold {self.config.min_pass_rate:.1%}"
            )

        if avg_score < self.config.min_average_score:
            pipeline_passed = False
            failure_reasons.append(
                f"Average score {avg_score:.2f} below threshold {self.config.min_average_score}"
            )

        if self.config.fail_on_critical:
            critical_count = sum(
                1 for r in test_results
                for issue in r.eval_result.issues
                if issue.severity == Severity.CRITICAL
            )
            if critical_count > 0:
                pipeline_passed = False
                failure_reasons.append(f"Found {critical_count} critical issues")

        # Create result
        result = PipelineResult(
            run_id=run_id,
            timestamp=start_time,
            duration_seconds=duration,
            total_tests=len(test_results),
            passed_tests=passed,
            failed_tests=failed,
            pass_rate=pass_rate,
            average_score=avg_score,
            pipeline_passed=pipeline_passed,
            failure_reasons=failure_reasons,
            test_results=test_results,
            quality_metrics=quality_metrics
        )

        # Generate reports
        result = await self._generate_reports(result)

        self.logger.info(
            f"Pipeline complete: {passed}/{len(test_results)} passed, "
            f"score={avg_score:.2f}, status={'PASSED' if pipeline_passed else 'FAILED'}"
        )

        return result

    async def run_with_mock_agents(self) -> PipelineResult:
        """
        Run pipeline with mock agent responses for testing

        Useful for:
        - Testing the eval framework itself
        - CI/CD when real agents aren't available
        - Development and debugging
        """
        mock_responses = {
            "architecture_design": {
                "architecture": {
                    "name": "Web Application Architecture",
                    "type": "three_tier",
                    "description": "Standard three-tier architecture"
                },
                "components": [
                    {"name": "Frontend", "type": "spa", "technology": "React"},
                    {"name": "Backend", "type": "api", "technology": "FastAPI"},
                    {"name": "Database", "type": "relational", "technology": "PostgreSQL"}
                ],
                "patterns": ["mvc", "repository", "dependency_injection"],
                "diagrams": ["component_diagram", "deployment_diagram"]
            },
            "pattern_recommendation": {
                "recommended_patterns": [
                    {"name": "Repository Pattern", "reason": "Abstracts data access"},
                    {"name": "Service Layer", "reason": "Business logic separation"}
                ]
            },
            "stack_recommendation": {
                "recommended_stack": {
                    "frontend": {"name": "React", "version": "18.x"},
                    "backend": {"name": "FastAPI", "version": "0.100+"},
                    "database": {"name": "PostgreSQL", "version": "15"},
                    "cache": {"name": "Redis", "version": "7"}
                },
                "rationale": "Modern, well-supported stack with excellent performance",
                "compatibility": {
                    "score": 0.95,
                    "notes": "All technologies have mature integrations"
                }
            },
            "technology_evaluation": {
                "evaluation": {
                    "technology": "FastAPI",
                    "pros": ["Fast", "Modern", "Type-safe"],
                    "cons": ["Smaller ecosystem than Flask"]
                },
                "score": 0.85
            },
            "documentation_generation": {
                "content": "# API Documentation\n\n## UserService\n\nHandles user management operations.",
                "format": "markdown",
                "sections": ["overview", "endpoints", "examples"]
            },
            "api_documentation": {
                "content": "# API Reference\n\n## Endpoints\n\n### GET /users",
                "format": "openapi"
            }
        }

        async def mock_executor(task_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
            """Mock agent executor that returns predefined responses"""
            import asyncio
            # Simulate some processing time
            await asyncio.sleep(0.1)

            response = mock_responses.get(task_type, {
                "result": "Mock response",
                "task_type": task_type
            })

            return response

        # Create executors for all agents
        agent_executors = {
            "architect-agent": mock_executor,
            "stack-recommender-agent": mock_executor,
            "document-agent": mock_executor
        }

        return await self.run(agent_executors)

    async def _generate_reports(self, result: PipelineResult) -> PipelineResult:
        """Generate output reports"""
        # Ensure output directory exists
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")

        # Create reporter
        reporter = EvalReporter(title=f"Agent Evaluation Report - Run {result.run_id}")
        reporter.add_test_case_results(result.test_results)

        # Generate markdown report
        if self.config.generate_markdown:
            md_path = output_dir / f"eval_report_{timestamp_str}.md"
            reporter.export_to_file(str(md_path), format="markdown")
            result.markdown_report_path = str(md_path)
            self.logger.info(f"Generated markdown report: {md_path}")

        # Generate JSON report
        if self.config.generate_json:
            json_path = output_dir / f"eval_report_{timestamp_str}.json"
            reporter.export_to_file(str(json_path), format="json")
            result.json_report_path = str(json_path)
            self.logger.info(f"Generated JSON report: {json_path}")

        # Save individual test results
        if self.config.save_individual_results:
            results_path = output_dir / f"test_results_{timestamp_str}.json"
            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(
                    [r.to_dict() for r in result.test_results],
                    f,
                    indent=2,
                    default=str
                )

        return result


async def run_quick_eval() -> PipelineResult:
    """
    Quick evaluation function for command-line usage

    Usage from CLI:
        python -m app.agents.shared.eval.pipeline
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    config = PipelineConfig(
        output_dir="./eval_results",
        generate_markdown=True,
        generate_json=True,
        min_pass_rate=0.6,  # Lower threshold for testing
        min_average_score=0.5
    )

    pipeline = EvalPipeline(config)
    result = await pipeline.run_with_mock_agents()

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Run ID: {result.run_id}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Tests: {result.passed_tests}/{result.total_tests} passed ({result.pass_rate:.1%})")
    print(f"Average Score: {result.average_score:.2f}")
    print(f"Status: {'[PASSED]' if result.pipeline_passed else '[FAILED]'}")

    if result.failure_reasons:
        print("\nFailure Reasons:")
        for reason in result.failure_reasons:
            print(f"  - {reason}")

    if result.markdown_report_path:
        print(f"\nReports generated:")
        print(f"  - Markdown: {result.markdown_report_path}")
        print(f"  - JSON: {result.json_report_path}")

    print("=" * 60)

    return result


if __name__ == "__main__":
    asyncio.run(run_quick_eval())
