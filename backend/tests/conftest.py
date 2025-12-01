"""
MMCODE Security Platform - Test Configuration & Fixtures
========================================================

공통 테스트 픽스처 및 설정
- 데이터베이스 세션 픽스처
- 보안 컴포넌트 픽스처
- 테스트 데이터 픽스처

Version: 1.0.0
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

# SQLAlchemy imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# App imports
from backend.app.models.models import Base
from backend.app.security.models import (
    SecurityAction, EngagementScope, PentestPhase, RiskLevel, 
    EngagementType, generate_action_id
)
from backend.app.security.approval_workflow import (
    ApprovalWorkflow, RiskEvaluator, ApprovalConfiguration
)
from backend.app.security.notifications import (
    NotificationManager, NotificationConfig, SMSConfig
)
from backend.app.security import (
    ScopeEnforcementEngine, SecurityAuditLogger
)


# ==================== 기본 설정 ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """이벤트 루프 생성"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """테스트용 데이터베이스 엔진"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


# ==================== 보안 컴포넌트 픽스처 ====================

@pytest.fixture
def scope_enforcer() -> ScopeEnforcementEngine:
    """범위 검증 엔진"""
    return ScopeEnforcementEngine()


@pytest.fixture
def audit_logger() -> SecurityAuditLogger:
    """감사 로거"""
    return SecurityAuditLogger()


@pytest.fixture
def risk_evaluator() -> RiskEvaluator:
    """위험도 평가기"""
    return RiskEvaluator()


@pytest.fixture
async def approval_workflow(db_session) -> ApprovalWorkflow:
    """승인 워크플로우"""
    return ApprovalWorkflow(db_session)


@pytest.fixture
def notification_config() -> NotificationConfig:
    """알림 설정 (테스트용)"""
    return NotificationConfig(
        from_email="test@mmcode.ai",
        smtp_server="localhost",
        smtp_port=587,
        smtp_use_tls=False,  # 테스트에서는 TLS 비활성화
        slack_webhook_url="https://hooks.slack.test/test",
        approver_contacts={
            "security_analyst": {
                "email": "analyst@test.mmcode.ai",
                "slack_user_id": "@test-analyst",
                "phone": "+82101234TEST"
            },
            "security_lead": {
                "email": "lead@test.mmcode.ai", 
                "slack_user_id": "@test-lead",
                "phone": "+82102345TEST"
            },
            "security_manager": {
                "email": "manager@test.mmcode.ai",
                "slack_user_id": "@test-manager",
                "phone": "+82103456TEST"
            },
            "ciso": {
                "email": "ciso@test.mmcode.ai",
                "slack_user_id": "@test-ciso",
                "phone": "+82104567TEST"
            }
        }
    )


@pytest.fixture
def sms_config() -> SMSConfig:
    """SMS 설정 (테스트용)"""
    return SMSConfig(
        aws_region="us-east-1",  # 테스트용 리전
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        sender_id="TEST",
        approver_phones={
            "security_analyst": "+82101234TEST",
            "security_lead": "+82102345TEST",
            "security_manager": "+82103456TEST",
            "ciso": "+82104567TEST"
        }
    )


@pytest.fixture
def notification_manager(notification_config, sms_config) -> NotificationManager:
    """알림 관리자 (Mock 설정)"""
    return NotificationManager(notification_config, sms_config)


# ==================== 테스트 데이터 픽스처 ====================

@pytest.fixture
def sample_scope() -> EngagementScope:
    """샘플 테스트 범위"""
    return EngagementScope(
        engagement_id="test_engagement_001",
        engagement_name="Test Security Engagement",
        engagement_type=EngagementType.INTERNAL,
        ip_ranges=["192.168.1.0/24", "10.0.1.0/24"],
        domains=["test.example.com", "*.internal.test"],
        excluded_ips=["192.168.1.1", "192.168.1.255"],
        excluded_ports=[22, 3389],  # SSH, RDP 제외
        allowed_ports=[80, 443, 8080, 8443],
        allowed_methods=["port_scan", "vuln_scan", "web_scan", "dns_enum"],
        prohibited_methods=["dos_attack", "data_exfiltration"],
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(days=7),
        requires_approval_above=RiskLevel.MEDIUM
    )


@pytest.fixture
def low_risk_action() -> SecurityAction:
    """저위험 작업"""
    return SecurityAction(
        action_id=generate_action_id(),
        action_type="port_scan",
        target="192.168.1.100",
        tool_name="nmap",
        command="nmap -sS -p 1-1000 192.168.1.100",
        phase=PentestPhase.SCANNING,
        risk_level=RiskLevel.LOW,
        requires_network=True,
        is_destructive=False
    )


@pytest.fixture
def medium_risk_action() -> SecurityAction:
    """중위험 작업"""
    return SecurityAction(
        action_id=generate_action_id(),
        action_type="vulnerability_scan",
        target="192.168.1.100",
        tool_name="nuclei",
        command="nuclei -u http://192.168.1.100 -t vulnerabilities/",
        phase=PentestPhase.VULNERABILITY_ASSESSMENT,
        risk_level=RiskLevel.MEDIUM,
        requires_network=True,
        is_destructive=False
    )


@pytest.fixture
def high_risk_action() -> SecurityAction:
    """고위험 작업"""
    return SecurityAction(
        action_id=generate_action_id(),
        action_type="exploitation",
        target="192.168.1.100",
        tool_name="metasploit",
        command="exploit/windows/smb/ms17_010_eternalblue",
        phase=PentestPhase.EXPLOITATION,
        risk_level=RiskLevel.HIGH,
        requires_network=True,
        is_destructive=True
    )


@pytest.fixture
def critical_risk_action() -> SecurityAction:
    """치명적 위험 작업"""
    return SecurityAction(
        action_id=generate_action_id(),
        action_type="data_exfiltration",
        target="192.168.1.10",  # DB 서버
        tool_name="custom",
        command="extract_sensitive_data.py --target 192.168.1.10",
        phase=PentestPhase.POST_EXPLOITATION,
        risk_level=RiskLevel.CRITICAL,
        requires_network=True,
        is_destructive=True
    )


# ==================== Mock 객체 픽스처 ====================

@pytest.fixture
def mock_tool_result():
    """Mock 도구 실행 결과"""
    class MockToolResult:
        success = True
        output = "Scan completed. Found 5 open ports."
        findings = [
            {"port": 22, "service": "ssh", "version": "OpenSSH 8.2"},
            {"port": 80, "service": "http", "version": "nginx 1.18"},
            {"port": 443, "service": "https", "version": "nginx 1.18"},
            {"port": 8080, "service": "http-alt", "version": "Tomcat 9.0"},
            {"port": 3306, "service": "mysql", "version": "MySQL 8.0"}
        ]
        execution_time = 15.5
    
    return MockToolResult()


@pytest.fixture
def mock_failed_tool_result():
    """Mock 실패한 도구 실행 결과"""
    class MockFailedResult:
        success = False
        output = "Connection timeout: Unable to reach target"
        findings = []
        execution_time = 30.0
        error_code = "TIMEOUT"
        error_message = "Target host is unreachable or blocking connections"
    
    return MockFailedResult()


@pytest.fixture
def async_mock():
    """비동기 Mock 헬퍼"""
    return AsyncMock


@pytest.fixture
def mock_notification_handlers():
    """Mock 알림 핸들러들"""
    return {
        "email": AsyncMock(return_value=True),
        "slack": AsyncMock(return_value=True),
        "sms": AsyncMock(return_value=True),
        "webhook": AsyncMock(return_value=True)
    }


# ==================== Agent System 픽스처 ====================

@pytest.fixture
async def mock_agent_manager(db_session, sample_scope):
    """Mock Agent System Manager"""
    from backend.app.agents import AgentSystemManager
    
    config = {
        "db_session": db_session,
        "scope": sample_scope,
        "test_mode": True
    }
    
    manager = AgentSystemManager(config)
    await manager.initialize()
    
    yield manager
    
    # Cleanup
    await manager.close()


@pytest.fixture
def mock_threat_analyzer():
    """Mock Threat Analyzer"""
    mock_analyzer = AsyncMock()
    
    # Mock recommendations
    mock_analyzer.get_recommendations.return_value = [
        type('MockTask', (), {
            'task_id': 'task_001',
            'task_type': 'port_scan',
            'target': '192.168.1.100',
            'tool': 'nmap',
            'command': 'nmap -sS -p 1-1000 192.168.1.100',
            'phase': PentestPhase.SCANNING,
            'risk_level': RiskLevel.LOW
        })(),
        type('MockTask', (), {
            'task_id': 'task_002', 
            'task_type': 'vuln_scan',
            'target': '192.168.1.100',
            'tool': 'nuclei',
            'command': 'nuclei -u http://192.168.1.100',
            'phase': PentestPhase.VULNERABILITY_ASSESSMENT,
            'risk_level': RiskLevel.MEDIUM
        })()
    ]
    
    return mock_analyzer


# ==================== 환경 및 설정 픽스처 ====================

@pytest.fixture
def test_environment():
    """테스트 환경 설정"""
    import os
    
    # 테스트용 환경 변수 설정
    test_env = {
        "TESTING": "true",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "APPROVAL_BASE_URL": "https://test.mmcode.ai",
        "AWS_REGION": "us-east-1",
        "SMS_SENDER_ID": "TEST",
        "NOTIFICATION_FROM_EMAIL": "test@mmcode.ai"
    }
    
    # 기존 환경 변수 백업
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_env
    
    # 환경 변수 복원
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def approval_config():
    """승인 워크플로우 설정"""
    return ApprovalConfiguration(
        auto_approve_low_risk=True,
        auto_approve_medium_risk=False,
        require_manager_for_high=True,
        require_ciso_for_critical=True,
        default_timeout_minutes=60,
        escalation_timeout_minutes=30
    )


# ==================== 유틸리티 픽스처 ====================

@pytest.fixture
def mock_time():
    """시간 Mock 유틸리티"""
    import time
    from unittest.mock import patch
    
    fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_time
        mock_datetime.utcnow.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield fixed_time


@pytest.fixture
def capture_logs():
    """로그 캡처 유틸리티"""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # 루트 로거에 핸들러 추가
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # 핸들러 제거
    logger.removeHandler(handler)


@pytest.fixture
def temp_file():
    """임시 파일 생성 유틸리티"""
    import tempfile
    import os
    
    temp_files = []
    
    def create_temp_file(content="", suffix=".txt"):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        temp_files.append(path)
        return path
    
    yield create_temp_file
    
    # 임시 파일 정리
    for path in temp_files:
        try:
            os.remove(path)
        except OSError:
            pass


# ==================== 테스트 마커 설정 ====================

def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "approval: Approval workflow tests")
    config.addinivalue_line("markers", "notification: Notification system tests")


# ==================== 테스트 사전/사후 처리 ====================

@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """테스트 데이터 자동 정리"""
    # 테스트 전 설정
    yield
    
    # 테스트 후 정리
    # 필요한 경우 여기에 정리 로직 추가
    pass


@pytest.fixture
def reset_singletons():
    """싱글톤 인스턴스 리셋"""
    # 싱글톤 패턴을 사용하는 클래스들의 인스턴스를 리셋
    # 테스트 간 독립성 보장
    
    yield
    
    # 테스트 후 싱글톤 리셋
    # 필요한 경우 여기에 싱글톤 리셋 로직 추가
    pass