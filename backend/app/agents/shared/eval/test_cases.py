"""
Evaluation Test Cases
=====================

Pre-defined test cases for each agent type to ensure consistent quality.
Based on the Open Coding methodology - these are derived from common issues.
"""

import json
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone
from enum import Enum

from .evaluator import AgentEvaluator, EvalResult, EvalCategory, Severity


class TestCaseCategory(Enum):
    """Test case categories"""
    HAPPY_PATH = "happy_path"           # 정상 케이스
    EDGE_CASE = "edge_case"             # 엣지 케이스
    ERROR_HANDLING = "error_handling"   # 에러 처리
    PERFORMANCE = "performance"         # 성능 테스트
    SECURITY = "security"               # 보안 테스트
    REGRESSION = "regression"           # 회귀 테스트


@dataclass
class EvalTestCase:
    """Single evaluation test case"""

    # Identification
    test_id: str
    name: str
    description: str
    agent_id: str
    task_type: str

    # Test Data
    input_context: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]] = None

    # Assertions
    must_contain_keys: List[str] = field(default_factory=list)
    must_not_contain: List[str] = field(default_factory=list)
    min_score: float = 0.7
    max_response_time_ms: float = 30000.0

    # Metadata
    category: TestCaseCategory = TestCaseCategory.HAPPY_PATH
    tags: List[str] = field(default_factory=list)
    priority: int = 1  # 1 = highest
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "category": self.category.value,
            "tags": self.tags,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class TestCaseResult:
    """Result of running a single test case"""
    test_case: EvalTestCase
    eval_result: EvalResult
    passed: bool
    failure_reason: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_case.test_id,
            "test_name": self.test_case.name,
            "passed": self.passed,
            "score": self.eval_result.score,
            "failure_reason": self.failure_reason,
            "execution_time_ms": self.execution_time_ms,
            "issues_count": len(self.eval_result.issues),
        }


class TestCaseRunner:
    """
    Runs evaluation test cases against agents

    Usage:
        runner = TestCaseRunner()
        runner.add_test_case(test_case)
        results = await runner.run_all(agent_executor)
    """

    def __init__(self):
        self.test_cases: List[EvalTestCase] = []
        self.results: List[TestCaseResult] = []
        self.logger = logging.getLogger("TestCaseRunner")

    def add_test_case(self, test_case: EvalTestCase):
        """Add a test case"""
        self.test_cases.append(test_case)

    def add_test_cases(self, test_cases: List[EvalTestCase]):
        """Add multiple test cases"""
        self.test_cases.extend(test_cases)

    async def run_all(
        self,
        agent_executor: Callable,
        parallel: bool = False,
        filter_tags: Optional[List[str]] = None,
        filter_category: Optional[TestCaseCategory] = None
    ) -> List[TestCaseResult]:
        """
        Run all test cases

        Args:
            agent_executor: Async function that takes (task_type, context) and returns response
            parallel: Run tests in parallel
            filter_tags: Only run tests with these tags
            filter_category: Only run tests in this category

        Returns:
            List of TestCaseResults
        """
        # Filter test cases
        cases_to_run = [tc for tc in self.test_cases if tc.enabled]

        if filter_tags:
            cases_to_run = [
                tc for tc in cases_to_run
                if any(tag in tc.tags for tag in filter_tags)
            ]

        if filter_category:
            cases_to_run = [
                tc for tc in cases_to_run
                if tc.category == filter_category
            ]

        # Sort by priority
        cases_to_run.sort(key=lambda x: x.priority)

        self.logger.info(f"Running {len(cases_to_run)} test cases")

        if parallel:
            tasks = [
                self._run_single_test(tc, agent_executor)
                for tc in cases_to_run
            ]
            self.results = await asyncio.gather(*tasks)
        else:
            self.results = []
            for tc in cases_to_run:
                result = await self._run_single_test(tc, agent_executor)
                self.results.append(result)

        return self.results

    async def _run_single_test(
        self,
        test_case: EvalTestCase,
        agent_executor: Callable
    ) -> TestCaseResult:
        """Run a single test case"""
        self.logger.info(f"Running test: {test_case.test_id} - {test_case.name}")

        start_time = datetime.now(timezone.utc)

        try:
            # Execute agent
            response = await agent_executor(
                test_case.task_type,
                test_case.input_context
            )
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # Evaluate response
            evaluator = AgentEvaluator(test_case.agent_id)
            eval_result = await evaluator.evaluate(
                task_type=test_case.task_type,
                input_context=test_case.input_context,
                agent_response=response,
                response_time_ms=execution_time,
                expected_output=test_case.expected_output
            )

            # Check assertions
            passed, failure_reason = self._check_assertions(
                test_case, eval_result, response, execution_time
            )

            return TestCaseResult(
                test_case=test_case,
                eval_result=eval_result,
                passed=passed,
                failure_reason=failure_reason,
                execution_time_ms=execution_time
            )

        except Exception as e:
            self.logger.error(f"Test {test_case.test_id} failed with exception: {e}")

            # Create failed eval result
            eval_result = EvalResult(
                eval_id="error",
                agent_id=test_case.agent_id,
                task_type=test_case.task_type,
                passed=False,
                score=0.0
            )

            return TestCaseResult(
                test_case=test_case,
                eval_result=eval_result,
                passed=False,
                failure_reason=f"Exception: {str(e)}",
                execution_time_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

    def _check_assertions(
        self,
        test_case: EvalTestCase,
        eval_result: EvalResult,
        response: Dict[str, Any],
        execution_time_ms: float
    ) -> tuple:
        """Check test case assertions"""
        response_str = json.dumps(response)

        # Check minimum score
        if eval_result.score < test_case.min_score:
            return False, f"Score {eval_result.score:.2f} below minimum {test_case.min_score}"

        # Check required keys
        for key in test_case.must_contain_keys:
            if key not in response:
                return False, f"Missing required key: {key}"

        # Check forbidden content
        for forbidden in test_case.must_not_contain:
            if forbidden.lower() in response_str.lower():
                return False, f"Response contains forbidden content: {forbidden}"

        # Check response time
        if execution_time_ms > test_case.max_response_time_ms:
            return False, f"Response time {execution_time_ms:.0f}ms exceeds max {test_case.max_response_time_ms:.0f}ms"

        return True, None

    def get_summary(self) -> Dict[str, Any]:
        """Get test run summary"""
        if not self.results:
            return {"message": "No tests run yet"}

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        # Group failures by category
        failures_by_category = {}
        for r in self.results:
            if not r.passed:
                category = r.test_case.category.value
                if category not in failures_by_category:
                    failures_by_category[category] = []
                failures_by_category[category].append({
                    "test_id": r.test_case.test_id,
                    "reason": r.failure_reason
                })

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self.results) if self.results else 0,
            "failures_by_category": failures_by_category,
            "average_score": sum(r.eval_result.score for r in self.results) / len(self.results),
            "average_execution_time_ms": sum(r.execution_time_ms for r in self.results) / len(self.results)
        }


# ===================
# Pre-defined Test Cases
# ===================

def get_architect_agent_test_cases() -> List[EvalTestCase]:
    """Get test cases for Architect Agent"""
    return [
        # Happy Path Tests
        EvalTestCase(
            test_id="arch-001",
            name="Basic Architecture Design",
            description="Test basic architecture design for a web application",
            agent_id="architect-agent",
            task_type="architecture_design",
            input_context={
                "analysis": {
                    "project_type": "web_application",
                    "features": ["user_auth", "api", "database"],
                    "scale": "medium"
                }
            },
            must_contain_keys=["architecture", "components"],
            min_score=0.7,
            category=TestCaseCategory.HAPPY_PATH,
            tags=["basic", "web"],
            priority=1
        ),
        EvalTestCase(
            test_id="arch-002",
            name="Microservices Architecture",
            description="Test architecture design for microservices",
            agent_id="architect-agent",
            task_type="architecture_design",
            input_context={
                "analysis": {
                    "project_type": "microservices",
                    "features": ["api_gateway", "service_mesh", "event_driven"],
                    "scale": "large"
                }
            },
            must_contain_keys=["architecture", "components", "patterns"],
            min_score=0.8,
            category=TestCaseCategory.HAPPY_PATH,
            tags=["microservices", "advanced"],
            priority=1
        ),

        # Edge Case Tests
        EvalTestCase(
            test_id="arch-edge-001",
            name="Minimal Requirements",
            description="Test with minimal input",
            agent_id="architect-agent",
            task_type="architecture_design",
            input_context={
                "analysis": {
                    "project_type": "unknown"
                }
            },
            min_score=0.5,
            category=TestCaseCategory.EDGE_CASE,
            tags=["edge", "minimal"],
            priority=2
        ),
        EvalTestCase(
            test_id="arch-edge-002",
            name="Complex Multi-Tier",
            description="Test complex multi-tier architecture",
            agent_id="architect-agent",
            task_type="architecture_design",
            input_context={
                "analysis": {
                    "project_type": "enterprise",
                    "features": ["sso", "multi_tenant", "analytics", "ml_pipeline", "realtime"],
                    "scale": "enterprise",
                    "compliance": ["gdpr", "soc2"]
                }
            },
            must_contain_keys=["architecture", "components", "diagrams"],
            min_score=0.7,
            category=TestCaseCategory.EDGE_CASE,
            tags=["complex", "enterprise"],
            priority=2
        ),

        # Error Handling Tests
        EvalTestCase(
            test_id="arch-err-001",
            name="Empty Analysis",
            description="Test with empty analysis input",
            agent_id="architect-agent",
            task_type="architecture_design",
            input_context={
                "analysis": {}
            },
            min_score=0.3,  # Lower threshold for error cases
            category=TestCaseCategory.ERROR_HANDLING,
            tags=["error", "empty"],
            priority=3
        ),
    ]


def get_stack_recommender_test_cases() -> List[EvalTestCase]:
    """Get test cases for Stack Recommender Agent"""
    return [
        EvalTestCase(
            test_id="stack-001",
            name="Basic Web Stack",
            description="Test stack recommendation for basic web app",
            agent_id="stack-recommender-agent",
            task_type="stack_recommendation",
            input_context={
                "architecture": {
                    "type": "web_application",
                    "layers": ["frontend", "backend", "database"]
                },
                "requirements": {
                    "scale": "small",
                    "team_size": 3
                }
            },
            must_contain_keys=["recommended_stack", "rationale"],
            min_score=0.7,
            category=TestCaseCategory.HAPPY_PATH,
            tags=["basic", "web"],
            priority=1
        ),
        EvalTestCase(
            test_id="stack-002",
            name="Modern Cloud Native Stack",
            description="Test stack for cloud native application",
            agent_id="stack-recommender-agent",
            task_type="stack_recommendation",
            input_context={
                "architecture": {
                    "type": "cloud_native",
                    "patterns": ["microservices", "event_driven", "containerized"]
                },
                "requirements": {
                    "scale": "large",
                    "cloud_provider": "aws"
                }
            },
            must_contain_keys=["recommended_stack", "rationale", "compatibility"],
            min_score=0.8,
            category=TestCaseCategory.HAPPY_PATH,
            tags=["cloud", "modern"],
            priority=1
        ),

        # Security Test
        EvalTestCase(
            test_id="stack-sec-001",
            name="No Deprecated Technologies",
            description="Ensure no deprecated/insecure technologies recommended",
            agent_id="stack-recommender-agent",
            task_type="stack_recommendation",
            input_context={
                "architecture": {
                    "type": "web_application"
                }
            },
            must_not_contain=["jquery 1.", "angular.js", "php 5", "python 2"],
            min_score=0.7,
            category=TestCaseCategory.SECURITY,
            tags=["security", "deprecated"],
            priority=1
        ),
    ]


def get_document_agent_test_cases() -> List[EvalTestCase]:
    """Get test cases for Document Agent"""
    return [
        EvalTestCase(
            test_id="doc-001",
            name="API Documentation",
            description="Test API documentation generation",
            agent_id="document-agent",
            task_type="documentation_generation",
            input_context={
                "architecture": {
                    "components": [
                        {"name": "UserService", "type": "api"}
                    ]
                },
                "doc_type": "api"
            },
            must_contain_keys=["content", "format"],
            min_score=0.7,
            category=TestCaseCategory.HAPPY_PATH,
            tags=["api", "basic"],
            priority=1
        ),
        EvalTestCase(
            test_id="doc-002",
            name="Full Project Documentation",
            description="Test complete project documentation",
            agent_id="document-agent",
            task_type="documentation_generation",
            input_context={
                "architecture": {
                    "name": "E-commerce Platform",
                    "components": [
                        {"name": "Frontend", "type": "ui"},
                        {"name": "Backend", "type": "api"},
                        {"name": "Database", "type": "storage"}
                    ]
                },
                "stack": {
                    "frontend": "React",
                    "backend": "FastAPI",
                    "database": "PostgreSQL"
                },
                "doc_type": "full"
            },
            must_contain_keys=["content"],
            min_score=0.8,
            category=TestCaseCategory.HAPPY_PATH,
            tags=["full", "comprehensive"],
            priority=1
        ),
    ]


def get_all_test_cases() -> List[EvalTestCase]:
    """Get all pre-defined test cases"""
    return (
        get_architect_agent_test_cases() +
        get_stack_recommender_test_cases() +
        get_document_agent_test_cases()
    )
