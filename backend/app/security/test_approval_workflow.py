"""
MMCODE Security Platform - Approval Workflow Test
=================================================

승인 워크플로우 기능 테스트 스크립트
- 기본 승인 요청 및 처리 테스트
- 위험도 평가 테스트
- 알림 시스템 테스트

Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from .models import (
    SecurityAction,
    generate_action_id,
    PentestPhase,
    RiskLevel,
    EngagementScope,
    EngagementType
)
from .approval_workflow import (
    ApprovalWorkflow,
    RiskEvaluator,
    ApprovalConfiguration,
    ApprovalResult
)
from .notifications import NotificationManager, NotificationConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockDBSession:
    """Mock database session for testing"""
    
    def __init__(self):
        self.data = {}
        self.committed = False
    
    def add(self, obj):
        self.data[getattr(obj, 'id', id(obj))] = obj
    
    async def commit(self):
        self.committed = True
        logger.info("Mock DB: Transaction committed")
    
    async def rollback(self):
        self.committed = False
        logger.info("Mock DB: Transaction rolled back")
    
    async def execute(self, query):
        # Mock query execution
        return MockResult()
    
    def flush(self):
        pass


class MockResult:
    """Mock query result"""
    
    def scalar_one_or_none(self):
        return None
    
    def scalars(self):
        return MockScalars()


class MockScalars:
    """Mock scalars result"""
    
    def all(self):
        return []


async def test_risk_evaluator():
    """위험도 평가 엔진 테스트"""
    logger.info("=== Testing Risk Evaluator ===")
    
    evaluator = RiskEvaluator()
    
    # 테스트 케이스 1: 저위험 스캔
    low_risk_action = SecurityAction(
        action_id=generate_action_id(),
        action_type="port_scan",
        target="192.168.1.100",
        tool_name="nmap",
        command="nmap -sS -p 1-1000 192.168.1.100",
        phase=PentestPhase.SCANNING,
        risk_level=RiskLevel.LOW
    )
    
    risk_assessment = await evaluator.assess_risk(low_risk_action)
    logger.info(f"Low risk action assessment:")
    logger.info(f"  Risk Level: {risk_assessment.risk_level.value}")
    logger.info(f"  Risk Score: {risk_assessment.risk_score:.2f}")
    logger.info(f"  Risk Factors: {risk_assessment.risk_factors}")
    
    # 테스트 케이스 2: 고위험 익스플로잇
    high_risk_action = SecurityAction(
        action_id=generate_action_id(),
        action_type="exploitation",
        target="192.168.1.100",
        tool_name="metasploit",
        command="exploit/windows/smb/ms17_010_eternalblue",
        phase=PentestPhase.EXPLOITATION,
        risk_level=RiskLevel.HIGH,
        is_destructive=True
    )
    
    risk_assessment = await evaluator.assess_risk(high_risk_action)
    logger.info(f"High risk action assessment:")
    logger.info(f"  Risk Level: {risk_assessment.risk_level.value}")
    logger.info(f"  Risk Score: {risk_assessment.risk_score:.2f}")
    logger.info(f"  Risk Factors: {risk_assessment.risk_factors}")
    logger.info(f"  Recommended Conditions: {risk_assessment.recommended_conditions}")
    
    return True


async def test_approval_workflow():
    """승인 워크플로우 테스트"""
    logger.info("=== Testing Approval Workflow ===")
    
    # Mock DB session
    db_session = MockDBSession()
    
    # 승인 워크플로우 초기화
    config = ApprovalConfiguration(
        auto_approve_below=RiskLevel.LOW,
        require_approval_above=RiskLevel.MEDIUM,
        default_timeout_minutes=30
    )
    
    workflow = ApprovalWorkflow(db_session=db_session, config=config)
    
    # 테스트 액션 생성
    action = SecurityAction(
        action_id=generate_action_id(),
        action_type="vulnerability_scan",
        target="example.com",
        tool_name="nuclei",
        command="nuclei -u https://example.com",
        phase=PentestPhase.VULNERABILITY_ASSESSMENT,
        risk_level=RiskLevel.MEDIUM
    )
    
    # 승인 요청
    try:
        request = await workflow.request_approval(
            action=action,
            requested_by="test_user",
            justification="Testing vulnerability assessment against staging environment",
            context={"test_mode": True}
        )
        
        logger.info(f"Approval request created:")
        logger.info(f"  Request ID: {request.request_id}")
        logger.info(f"  Status: {request.status.value}")
        logger.info(f"  Required Approver Role: {request.required_approver_role}")
        logger.info(f"  Timeout: {request.timeout_at}")
        
        # 승인 처리 시뮬레이션
        approval_result = await workflow.process_approval(
            request_id=request.request_id,
            approved=True,
            approver_id="security_lead",
            reason="Approved for testing purposes",
            conditions_accepted=request.approval_conditions
        )
        
        logger.info(f"Approval processed: {approval_result.value}")
        
        # 승인 상태 확인
        approval_status = await workflow.check_action_approval(action.action_id)
        if approval_status:
            logger.info(f"Action approval confirmed:")
            logger.info(f"  Granted: {approval_status.granted}")
            logger.info(f"  Approver: {approval_status.approver}")
            logger.info(f"  Valid: {approval_status.is_valid()}")
        
        return True
        
    except Exception as e:
        logger.error(f"Approval workflow test failed: {str(e)}")
        return False


async def test_notification_system():
    """알림 시스템 테스트"""
    logger.info("=== Testing Notification System ===")
    
    # 알림 설정
    config = NotificationConfig(
        from_email="test@mmcode.ai",
        smtp_server="localhost",
        smtp_port=587
    )
    
    notification_manager = NotificationManager(config)
    
    # 테스트 승인 요청 생성
    action = SecurityAction(
        action_id=generate_action_id(),
        action_type="exploitation",
        target="test.example.com",
        tool_name="metasploit",
        phase=PentestPhase.EXPLOITATION,
        risk_level=RiskLevel.HIGH
    )
    
    # Mock approval request
    class MockApprovalRequest:
        def __init__(self):
            self.request_id = generate_action_id()
            self.action = action
            self.requested_by = "test_user"
            self.requested_at = datetime.now(timezone.utc)
            self.timeout_at = datetime.now(timezone.utc) + timedelta(hours=2)
            self.required_approver_role = "security_manager"
            self.justification = "Critical vulnerability exploitation test"
            self.approval_conditions = ["Real-time monitoring", "Rollback plan ready"]
            self.status = ApprovalResult.PENDING
            
            # Mock risk assessment
            class MockRiskAssessment:
                risk_level = RiskLevel.HIGH
                risk_score = 0.8
                risk_factors = ["High impact tool", "Production environment"]
                impact_assessment = "Potential system compromise"
                likelihood = "Medium"
            
            self.risk_assessment = MockRiskAssessment()
            
            # Mock other attributes
            self.notified_approvers = []
            self.approved_by = None
            self.approved_at = None
            self.denial_reason = None
    
    request = MockApprovalRequest()
    
    # Mock notification handlers
    async def mock_email_handler(req, notification_type):
        logger.info(f"Mock Email: {notification_type} for {req.request_id}")
        return True
    
    async def mock_slack_handler(req, notification_type):
        logger.info(f"Mock Slack: {notification_type} for {req.request_id}")
        return True
    
    # Register mock handlers
    from .notifications import NotificationChannel
    notification_manager.register_notification_handler(
        NotificationChannel.EMAIL, mock_email_handler
    )
    notification_manager.register_notification_handler(
        NotificationChannel.SLACK, mock_slack_handler
    )
    
    try:
        # 승인 요청 알림 테스트
        results = await notification_manager.send_notification(
            request, "approval_request"
        )
        logger.info(f"Approval request notification results: {results}")
        
        # 승인 결과 알림 테스트
        request.status = ApprovalResult.APPROVED
        request.approved_by = "security_manager"
        request.approved_at = datetime.now(timezone.utc)
        
        results = await notification_manager.send_notification(
            request, "approval_result"
        )
        logger.info(f"Approval result notification results: {results}")
        
        return True
        
    except Exception as e:
        logger.error(f"Notification system test failed: {str(e)}")
        return False


async def test_integration_scenarios():
    """통합 시나리오 테스트"""
    logger.info("=== Testing Integration Scenarios ===")
    
    try:
        # 시나리오 1: 자동 승인 (저위험)
        logger.info("Scenario 1: Auto-approval for low-risk action")
        
        low_risk_action = SecurityAction(
            action_id=generate_action_id(),
            action_type="port_scan",
            target="192.168.1.0/24",
            tool_name="nmap",
            phase=PentestPhase.SCANNING,
            risk_level=RiskLevel.LOW
        )
        
        db_session = MockDBSession()
        config = ApprovalConfiguration(auto_approve_below=RiskLevel.MEDIUM)
        workflow = ApprovalWorkflow(db_session=db_session, config=config)
        
        request = await workflow.request_approval(
            action=low_risk_action,
            requested_by="automated_scanner",
            justification="Automated network discovery"
        )
        
        logger.info(f"Auto-approval result: {request.status.value}")
        
        # 시나리오 2: 승인 타임아웃
        logger.info("Scenario 2: Approval timeout")
        
        high_risk_action = SecurityAction(
            action_id=generate_action_id(),
            action_type="exploitation",
            target="critical.example.com",
            tool_name="metasploit",
            phase=PentestPhase.EXPLOITATION,
            risk_level=RiskLevel.CRITICAL
        )
        
        # 매우 짧은 타임아웃으로 테스트
        config_short_timeout = ApprovalConfiguration(
            critical_timeout_minutes=0.01  # 0.6초
        )
        workflow_timeout = ApprovalWorkflow(
            db_session=MockDBSession(), 
            config=config_short_timeout
        )
        
        request = await workflow_timeout.request_approval(
            action=high_risk_action,
            requested_by="penetration_tester",
            justification="Critical system exploitation test"
        )
        
        logger.info(f"Request created with short timeout: {request.request_id}")
        
        # 시나리오 3: 승인 거부
        logger.info("Scenario 3: Approval denial")
        
        denial_action = SecurityAction(
            action_id=generate_action_id(),
            action_type="data_extraction",
            target="database.example.com",
            command="mysqldump -u admin -p --all-databases",
            phase=PentestPhase.POST_EXPLOITATION,
            risk_level=RiskLevel.CRITICAL,
            is_destructive=True
        )
        
        workflow_denial = ApprovalWorkflow(db_session=MockDBSession())
        
        request = await workflow_denial.request_approval(
            action=denial_action,
            requested_by="external_contractor",
            justification="Database security assessment"
        )
        
        # 승인 거부
        result = await workflow_denial.process_approval(
            request_id=request.request_id,
            approved=False,
            approver_id="ciso",
            reason="Too high risk for external contractor execution"
        )
        
        logger.info(f"Denial result: {result.value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Integration scenarios test failed: {str(e)}")
        return False


async def run_all_tests():
    """모든 테스트 실행"""
    logger.info("Starting MMCODE Security Platform Approval Workflow Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Risk Evaluator", test_risk_evaluator),
        ("Approval Workflow", test_approval_workflow),
        ("Notification System", test_notification_system),
        ("Integration Scenarios", test_integration_scenarios)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            logger.info(f"Running test: {test_name}")
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {str(e)}")
            results[test_name] = False
        
        logger.info("-" * 40)
    
    # 결과 요약
    logger.info("=" * 60)
    logger.info("Test Results Summary:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Approval workflow is ready for production.")
    else:
        logger.warning("⚠️  Some tests failed. Please review the issues before deployment.")
    
    return passed == total


if __name__ == "__main__":
    # 비동기 테스트 실행
    asyncio.run(run_all_tests())