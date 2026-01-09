"""
MMCODE Agent Evaluation Framework
=================================

Implementation of systematic agent evaluation based on the 3-step methodology:
1. Open Coding - Collect raw observations from agent responses
2. Categorization - Group issues into patterns with priorities
3. Benevolent Dictator - Single domain expert defines quality criteria

This framework provides:
- Automated evaluation of agent responses
- Quality metrics tracking
- Issue pattern detection
- Regression testing support
"""

from .evaluator import AgentEvaluator, EvalResult, EvalCategory, Severity, EvalIssue
from .metrics import QualityMetrics, ResponseMetrics, MetricsCollector, create_pivot_table
from .test_cases import (
    EvalTestCase,
    TestCaseRunner,
    TestCaseResult,
    TestCaseCategory,
    get_architect_agent_test_cases,
    get_stack_recommender_test_cases,
    get_document_agent_test_cases,
    get_all_test_cases
)
from .reporter import EvalReporter, EvalReport
from .pipeline import EvalPipeline, PipelineConfig, PipelineResult, run_quick_eval

__all__ = [
    # Evaluator
    'AgentEvaluator',
    'EvalResult',
    'EvalCategory',
    'Severity',
    'EvalIssue',
    # Metrics
    'QualityMetrics',
    'ResponseMetrics',
    'MetricsCollector',
    'create_pivot_table',
    # Test Cases
    'EvalTestCase',
    'TestCaseRunner',
    'TestCaseResult',
    'TestCaseCategory',
    'get_architect_agent_test_cases',
    'get_stack_recommender_test_cases',
    'get_document_agent_test_cases',
    'get_all_test_cases',
    # Reporter
    'EvalReporter',
    'EvalReport',
    # Pipeline
    'EvalPipeline',
    'PipelineConfig',
    'PipelineResult',
    'run_quick_eval',
]
