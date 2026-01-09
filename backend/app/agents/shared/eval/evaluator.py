"""
Agent Evaluator - Core evaluation logic
=======================================

Implements the 3-step evaluation methodology:
1. Open Coding: Raw issue detection
2. Categorization: Pattern grouping
3. Priority Assessment: Business impact ranking
"""

import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class EvalCategory(Enum):
    """Evaluation issue categories based on Open Coding patterns"""

    # Format & Structure Issues
    FORMAT_ERROR = "format_error"           # JSON 깨짐, 스키마 불일치
    INCOMPLETE_RESPONSE = "incomplete"      # 필수 필드 누락
    VERBOSE_RESPONSE = "verbose"            # 답변이 너무 장황함

    # Content Quality Issues
    HALLUCINATION = "hallucination"         # 잘못된 정보, 존재하지 않는 기능
    INACCURATE_INFO = "inaccurate"          # 부정확한 정보
    OUTDATED_INFO = "outdated"              # 구식 정보

    # Reasoning Issues
    POOR_REASONING = "poor_reasoning"       # 논리적 오류
    MISSING_CONTEXT = "missing_context"     # 컨텍스트 무시
    WRONG_ASSUMPTION = "wrong_assumption"   # 잘못된 가정

    # Compliance Issues
    TONE_VIOLATION = "tone_violation"       # 톤앤매너 위반
    SCOPE_VIOLATION = "scope_violation"     # 범위 초과 응답
    SECURITY_LEAK = "security_leak"         # 민감 정보 노출

    # Performance Issues
    SLOW_RESPONSE = "slow_response"         # 응답 지연
    TIMEOUT = "timeout"                     # 타임아웃

    # Success
    PASS = "pass"                           # 모든 검증 통과


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"    # 비즈니스 치명적 (즉시 수정 필요)
    HIGH = "high"            # 사용자 경험 저해
    MEDIUM = "medium"        # 품질 저하
    LOW = "low"              # 개선 권장


@dataclass
class EvalIssue:
    """Single evaluation issue found"""
    category: EvalCategory
    severity: Severity
    description: str
    evidence: Optional[str] = None
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class EvalResult:
    """Complete evaluation result for a single agent response"""

    # Identification
    eval_id: str
    agent_id: str
    task_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Input/Output
    input_context: Dict[str, Any] = field(default_factory=dict)
    agent_response: Dict[str, Any] = field(default_factory=dict)

    # Evaluation Results
    passed: bool = False
    score: float = 0.0  # 0.0 ~ 1.0
    issues: List[EvalIssue] = field(default_factory=list)

    # Metrics
    response_time_ms: float = 0.0
    token_count: int = 0

    # Metadata
    evaluator_version: str = "1.0.0"
    evaluation_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.passed,
            "score": self.score,
            "issues": [
                {
                    "category": issue.category.value,
                    "severity": issue.severity.value,
                    "description": issue.description,
                    "evidence": issue.evidence,
                    "suggestion": issue.suggestion
                }
                for issue in self.issues
            ],
            "response_time_ms": self.response_time_ms,
            "token_count": self.token_count,
            "evaluator_version": self.evaluator_version,
        }


class AgentEvaluator:
    """
    Main evaluator class implementing the 3-step methodology

    Usage:
        evaluator = AgentEvaluator(agent_id="architect-agent")
        result = await evaluator.evaluate(
            task_type="architecture_design",
            input_context={"requirements": "..."},
            agent_response={"architecture": {...}}
        )
    """

    def __init__(
        self,
        agent_id: str,
        strict_mode: bool = False,
        custom_validators: Optional[List[Callable]] = None
    ):
        self.agent_id = agent_id
        self.strict_mode = strict_mode
        self.custom_validators = custom_validators or []
        self.logger = logging.getLogger(f"Evaluator.{agent_id}")

        # Built-in validators per category
        self._validators = {
            "format": self._validate_format,
            "content": self._validate_content,
            "reasoning": self._validate_reasoning,
            "compliance": self._validate_compliance,
        }

    async def evaluate(
        self,
        task_type: str,
        input_context: Dict[str, Any],
        agent_response: Dict[str, Any],
        response_time_ms: float = 0.0,
        expected_output: Optional[Dict[str, Any]] = None
    ) -> EvalResult:
        """
        Evaluate an agent response

        Args:
            task_type: Type of task (e.g., "architecture_design")
            input_context: Original input to the agent
            agent_response: Agent's response
            response_time_ms: Response time in milliseconds
            expected_output: Optional expected output for comparison

        Returns:
            EvalResult with detailed evaluation
        """
        import uuid

        result = EvalResult(
            eval_id=str(uuid.uuid4())[:8],
            agent_id=self.agent_id,
            task_type=task_type,
            input_context=input_context,
            agent_response=agent_response,
            response_time_ms=response_time_ms
        )

        all_issues: List[EvalIssue] = []

        # Step 1: Open Coding - Run all validators
        for validator_name, validator_fn in self._validators.items():
            try:
                issues = await validator_fn(
                    task_type, input_context, agent_response, expected_output
                )
                all_issues.extend(issues)
            except Exception as e:
                self.logger.error(f"Validator {validator_name} failed: {e}")
                all_issues.append(EvalIssue(
                    category=EvalCategory.FORMAT_ERROR,
                    severity=Severity.HIGH,
                    description=f"Validator error: {str(e)}"
                ))

        # Run custom validators
        for custom_validator in self.custom_validators:
            try:
                issues = await custom_validator(
                    task_type, input_context, agent_response
                )
                all_issues.extend(issues)
            except Exception as e:
                self.logger.warning(f"Custom validator failed: {e}")

        # Step 2: Categorization & Priority
        result.issues = self._prioritize_issues(all_issues)

        # Step 3: Calculate final score
        result.score = self._calculate_score(result.issues)
        result.passed = self._determine_pass(result.score, result.issues)

        return result

    async def _validate_format(
        self,
        task_type: str,
        input_context: Dict[str, Any],
        response: Dict[str, Any],
        expected: Optional[Dict[str, Any]]
    ) -> List[EvalIssue]:
        """Validate response format and structure"""
        issues = []

        # Check if response is valid JSON-serializable
        try:
            json.dumps(response)
        except (TypeError, ValueError) as e:
            issues.append(EvalIssue(
                category=EvalCategory.FORMAT_ERROR,
                severity=Severity.CRITICAL,
                description="Response is not JSON serializable",
                evidence=str(e)[:200]
            ))
            return issues  # Critical error, stop here

        # Check for empty response
        if not response:
            issues.append(EvalIssue(
                category=EvalCategory.INCOMPLETE_RESPONSE,
                severity=Severity.HIGH,
                description="Empty response received"
            ))
            return issues

        # Check for required fields based on task type
        required_fields = self._get_required_fields(task_type)
        for field in required_fields:
            if field not in response or response[field] is None:
                issues.append(EvalIssue(
                    category=EvalCategory.INCOMPLETE_RESPONSE,
                    severity=Severity.HIGH,
                    description=f"Missing required field: {field}",
                    suggestion=f"Ensure {field} is included in response"
                ))

        # Check for verbose response
        response_str = json.dumps(response)
        if len(response_str) > 50000:  # Arbitrary threshold
            issues.append(EvalIssue(
                category=EvalCategory.VERBOSE_RESPONSE,
                severity=Severity.LOW,
                description=f"Response is very large ({len(response_str)} chars)",
                suggestion="Consider summarizing or paginating response"
            ))

        return issues

    async def _validate_content(
        self,
        task_type: str,
        input_context: Dict[str, Any],
        response: Dict[str, Any],
        expected: Optional[Dict[str, Any]]
    ) -> List[EvalIssue]:
        """Validate content accuracy and relevance"""
        issues = []

        # Check for hallucination indicators
        hallucination_keywords = [
            "as of my knowledge cutoff",
            "I don't have access to",
            "I cannot verify",
            "this may not be accurate"
        ]

        response_str = json.dumps(response).lower()
        for keyword in hallucination_keywords:
            if keyword in response_str:
                issues.append(EvalIssue(
                    category=EvalCategory.HALLUCINATION,
                    severity=Severity.MEDIUM,
                    description=f"Potential uncertainty indicator: '{keyword}'",
                    evidence=keyword
                ))

        # If expected output provided, compare
        if expected:
            similarity = self._calculate_similarity(response, expected)
            if similarity < 0.5:
                issues.append(EvalIssue(
                    category=EvalCategory.INACCURATE_INFO,
                    severity=Severity.HIGH,
                    description=f"Response differs significantly from expected (similarity: {similarity:.2f})"
                ))

        return issues

    async def _validate_reasoning(
        self,
        task_type: str,
        input_context: Dict[str, Any],
        response: Dict[str, Any],
        expected: Optional[Dict[str, Any]]
    ) -> List[EvalIssue]:
        """Validate reasoning quality"""
        issues = []

        # Check if context was considered
        input_keys = set(input_context.keys())
        response_str = json.dumps(response).lower()

        # For architecture design, check if requirements are reflected
        if task_type == "architecture_design":
            if "requirements" in input_context:
                requirements_text = str(input_context.get("requirements", "")).lower()
                key_terms = [term for term in requirements_text.split() if len(term) > 5][:10]

                found_terms = sum(1 for term in key_terms if term in response_str)
                if key_terms and found_terms / len(key_terms) < 0.3:
                    issues.append(EvalIssue(
                        category=EvalCategory.MISSING_CONTEXT,
                        severity=Severity.MEDIUM,
                        description="Response may not adequately address input requirements",
                        suggestion="Ensure key requirements are reflected in the design"
                    ))

        return issues

    async def _validate_compliance(
        self,
        task_type: str,
        input_context: Dict[str, Any],
        response: Dict[str, Any],
        expected: Optional[Dict[str, Any]]
    ) -> List[EvalIssue]:
        """Validate compliance with policies"""
        issues = []

        response_str = json.dumps(response)

        # Check for potential security leaks
        sensitive_patterns = [
            "password", "api_key", "secret", "token",
            "private_key", "credential"
        ]

        for pattern in sensitive_patterns:
            if pattern in response_str.lower():
                # Check if it's just a field name vs actual value
                if f'"{pattern}"' not in response_str.lower():
                    issues.append(EvalIssue(
                        category=EvalCategory.SECURITY_LEAK,
                        severity=Severity.CRITICAL,
                        description=f"Potential sensitive data in response: {pattern}",
                        suggestion="Review and redact any sensitive information"
                    ))

        return issues

    def _get_required_fields(self, task_type: str) -> List[str]:
        """Get required fields for a task type"""
        required_fields_map = {
            "architecture_design": ["architecture", "components"],
            "pattern_recommendation": ["recommended_patterns"],
            "stack_recommendation": ["recommended_stack", "rationale"],
            "technology_evaluation": ["evaluation", "score"],
            "documentation_generation": ["content", "format"],
            "requirement_analysis": ["features", "constraints"],
        }
        return required_fields_map.get(task_type, [])

    def _prioritize_issues(self, issues: List[EvalIssue]) -> List[EvalIssue]:
        """Sort issues by severity (Step 2: Categorization)"""
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3
        }
        return sorted(issues, key=lambda x: severity_order.get(x.severity, 4))

    def _calculate_score(self, issues: List[EvalIssue]) -> float:
        """Calculate overall quality score"""
        if not issues:
            return 1.0

        # Deduction per severity
        deductions = {
            Severity.CRITICAL: 0.4,
            Severity.HIGH: 0.2,
            Severity.MEDIUM: 0.1,
            Severity.LOW: 0.05
        }

        total_deduction = sum(
            deductions.get(issue.severity, 0.1)
            for issue in issues
        )

        return max(0.0, 1.0 - total_deduction)

    def _determine_pass(self, score: float, issues: List[EvalIssue]) -> bool:
        """Determine if evaluation passes (Step 3: Benevolent Dictator decision)"""
        # Fail on any critical issue
        has_critical = any(
            issue.severity == Severity.CRITICAL
            for issue in issues
        )
        if has_critical:
            return False

        # Pass threshold
        if self.strict_mode:
            return score >= 0.9
        else:
            return score >= 0.7

    def _calculate_similarity(
        self,
        response: Dict[str, Any],
        expected: Dict[str, Any]
    ) -> float:
        """Calculate similarity between response and expected output"""
        # Simple key overlap for now
        response_keys = set(self._flatten_keys(response))
        expected_keys = set(self._flatten_keys(expected))

        if not expected_keys:
            return 1.0

        intersection = response_keys & expected_keys
        return len(intersection) / len(expected_keys)

    def _flatten_keys(self, d: Dict[str, Any], prefix: str = "") -> List[str]:
        """Flatten nested dict keys"""
        keys = []
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.append(full_key)
            if isinstance(v, dict):
                keys.extend(self._flatten_keys(v, full_key))
        return keys
