"""
End-to-End Test: Audit Log Verification Workflow
===============================================

Test scenario: Complete workflow → audit log verification

This test validates the complete audit logging system including:
1. Audit event generation throughout security workflows
2. Hash chain integrity verification for immutable logging
3. Session-based audit trail correlation
4. Event type coverage and completeness
5. Audit log storage and retrieval verification
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.audit_logger import SecurityAuditLogger, AuditEvent, AuditEventType
from app.security.approval_integration import ApprovalIntegrationManager
from app.security.models import SecurityAction, generate_action_id, PentestPhase, RiskLevel
from app.tools.base import BaseSecurityTool, ToolResult
from app.models.models import SecurityAuditLog, Session, HumanApproval


class TestAuditLogVerification:
    """E2E test suite for audit log verification"""

    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session for audit logging"""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        return session

    @pytest.fixture
    async def audit_logger(self, mock_db_session):
        """Audit logger instance for testing"""
        return SecurityAuditLogger(
            db_session=mock_db_session,
            enable_file_logging=True,
            enable_hash_chain=True
        )

    @pytest.fixture
    def sample_security_session(self):
        """Sample security testing session"""
        return Session(
            session_id="test_session_audit_123",
            user_id="security_analyst_1",
            status="active",
            created_at=datetime.now(timezone.utc),
            metadata={
                "engagement_id": "PENTEST_2024_001",
                "target_scope": ["192.168.1.0/24"],
                "authorized_tools": ["nmap", "nuclei", "metasploit"]
            }
        )

    @pytest.fixture
    def sample_security_action(self):
        """Sample security action for audit testing"""
        return SecurityAction(
            action_id=generate_action_id(),
            action_type="vulnerability_scan",
            target="192.168.1.100",
            tool_name="nuclei",
            method="cve_scan",
            phase=PentestPhase.SCANNING,
            risk_level=RiskLevel.MEDIUM,
            justification="CVE scanning for critical vulnerabilities",
            requested_by="security_analyst_1"
        )

    @pytest.mark.asyncio
    async def test_complete_audit_workflow_coverage(
        self,
        audit_logger,
        sample_security_session,
        sample_security_action
    ):
        """Test complete audit log coverage for security workflow"""
        
        session_id = sample_security_session.session_id
        
        # Test session lifecycle audit events
        await audit_logger.log_session_started(
            session_id=session_id,
            user_id="security_analyst_1",
            engagement_details={
                "engagement_id": "PENTEST_2024_001",
                "scope": ["192.168.1.0/24"]
            }
        )
        
        # Test action proposal audit event
        await audit_logger.log_action_proposed(
            session_id=session_id,
            action=sample_security_action,
            context={
                "automation_level": "semi_automated",
                "risk_score": 0.6
            }
        )
        
        # Test scope validation audit event
        await audit_logger.log_scope_validation(
            session_id=session_id,
            action=sample_security_action,
            validation_result={
                "valid": True,
                "message": "Target within approved scope",
                "validator": "ScopeEnforcementEngine"
            }
        )
        
        # Test tool execution audit event
        await audit_logger.log_tool_execution(
            session_id=session_id,
            action=sample_security_action,
            tool_result={
                "success": True,
                "findings_count": 3,
                "execution_time": 45.2,
                "output_size": 2048
            }
        )
        
        # Test finding discovery audit event
        await audit_logger.log_finding_discovered(
            session_id=session_id,
            finding={
                "finding_id": "CVE_2021_44228_001",
                "severity": "critical",
                "cve_id": "CVE-2021-44228",
                "target": "192.168.1.100:8080",
                "confidence": 0.95
            },
            context={
                "detection_method": "nuclei_template",
                "template_id": "CVE-2021-44228"
            }
        )
        
        # Test session end audit event
        await audit_logger.log_session_ended(
            session_id=session_id,
            session_summary={
                "duration_seconds": 3600,
                "actions_executed": 5,
                "findings_discovered": 8,
                "critical_findings": 2
            }
        )
        
        # Verify audit log entries were created
        assert audit_logger.db_session.add.call_count == 6
        assert audit_logger.db_session.commit.call_count == 6
        
        # Verify event types coverage
        expected_event_types = [
            AuditEventType.SESSION_STARTED,
            AuditEventType.ACTION_PROPOSED,
            AuditEventType.SCOPE_VALIDATION,
            AuditEventType.TOOL_EXECUTION,
            AuditEventType.FINDING_DISCOVERED,
            AuditEventType.SESSION_ENDED
        ]
        
        # Extract event types from add() calls
        added_events = [call.args[0] for call in audit_logger.db_session.add.call_args_list]
        added_event_types = [event.event_type for event in added_events if hasattr(event, 'event_type')]
        
        for expected_type in expected_event_types:
            assert expected_type in added_event_types

    @pytest.mark.asyncio
    async def test_audit_hash_chain_integrity(
        self,
        audit_logger,
        sample_security_session
    ):
        """Test audit hash chain integrity verification"""
        
        session_id = sample_security_session.session_id
        
        # Create sequence of audit events
        events = []
        
        # Event 1: Session start
        event1 = await audit_logger.log_session_started(
            session_id=session_id,
            user_id="security_analyst_1",
            engagement_details={"engagement_id": "PENTEST_2024_001"}
        )
        events.append(event1)
        
        # Event 2: Action execution
        event2 = await audit_logger.log_action_executed(
            session_id=session_id,
            action_id="action_001",
            execution_details={
                "tool": "nmap",
                "target": "192.168.1.100",
                "result": "success"
            }
        )
        events.append(event2)
        
        # Event 3: Finding discovered
        event3 = await audit_logger.log_finding_discovered(
            session_id=session_id,
            finding={
                "finding_id": "finding_001",
                "type": "open_port",
                "port": 22,
                "service": "ssh"
            }
        )
        events.append(event3)
        
        # Verify hash chain integrity
        for i, event in enumerate(events):
            if i == 0:
                # First event should have no previous hash
                assert event.previous_hash is None or event.previous_hash == ""
            else:
                # Subsequent events should chain to previous event
                previous_event = events[i-1]
                assert event.previous_hash == previous_event.integrity_hash
            
            # Verify event hash integrity
            assert event.integrity_hash is not None
            assert len(event.integrity_hash) > 0
            
            # Verify hash includes critical fields
            hash_content = audit_logger._build_hash_content(event)
            assert event.event_id in hash_content
            assert event.session_id in hash_content
            assert event.timestamp.isoformat() in hash_content

    @pytest.mark.asyncio 
    async def test_audit_log_approval_workflow_integration(
        self,
        audit_logger,
        sample_security_session
    ):
        """Test audit logging integration with approval workflow"""
        
        session_id = sample_security_session.session_id
        
        # High-risk action requiring approval
        high_risk_action = SecurityAction(
            action_id="high_risk_001",
            action_type="exploit_execution", 
            target="192.168.1.100",
            tool_name="metasploit",
            method="reverse_shell",
            phase=PentestPhase.EXPLOITATION,
            risk_level=RiskLevel.HIGH,
            requires_approval=True
        )
        
        # Log approval request
        await audit_logger.log_action_proposed(
            session_id=session_id,
            action=high_risk_action,
            context={"requires_approval": True, "risk_score": 0.9}
        )
        
        # Log approval granted
        await audit_logger.log_action_approved(
            session_id=session_id,
            action_id=high_risk_action.action_id,
            approval_details={
                "approved_by": "security_manager_1",
                "approval_timestamp": datetime.now(timezone.utc).isoformat(),
                "conditions": ["monitor_execution", "limit_scope"],
                "justification": "Critical vulnerability testing approved"
            }
        )
        
        # Log action execution post-approval
        await audit_logger.log_action_executed(
            session_id=session_id,
            action_id=high_risk_action.action_id,
            execution_details={
                "approved": True,
                "execution_start": datetime.now(timezone.utc).isoformat(),
                "conditions_applied": ["monitor_execution", "limit_scope"]
            }
        )
        
        # Verify approval workflow audit trail
        assert audit_logger.db_session.add.call_count == 3
        
        # Verify audit events include approval context
        added_events = [call.args[0] for call in audit_logger.db_session.add.call_args_list]
        
        # Check approval-related audit details
        approval_event = added_events[1]  # Second event (approval granted)
        assert approval_event.event_type == AuditEventType.ACTION_APPROVED
        assert "security_manager_1" in approval_event.details.get("approved_by", "")

    @pytest.mark.asyncio
    async def test_audit_log_error_and_violation_handling(
        self,
        audit_logger,
        sample_security_session
    ):
        """Test audit logging for errors and security violations"""
        
        session_id = sample_security_session.session_id
        
        # Log scope violation
        await audit_logger.log_scope_violation(
            session_id=session_id,
            violation_details={
                "attempted_target": "8.8.8.8",
                "violation_type": "external_target",
                "blocked_by": "ScopeEnforcementEngine",
                "severity": "high",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Log emergency stop
        await audit_logger.log_emergency_stop(
            session_id=session_id,
            stop_details={
                "reason": "unauthorized_activity_detected",
                "triggered_by": "automated_monitoring",
                "affected_actions": ["action_001", "action_002"],
                "stop_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Log human intervention
        await audit_logger.log_human_intervention(
            session_id=session_id,
            intervention_details={
                "intervention_type": "manual_override", 
                "operator_id": "security_lead_1",
                "reason": "false_positive_detection",
                "actions_modified": ["action_003"]
            }
        )
        
        # Verify critical events are logged
        assert audit_logger.db_session.add.call_count == 3
        
        added_events = [call.args[0] for call in audit_logger.db_session.add.call_args_list]
        event_types = [event.event_type for event in added_events]
        
        assert AuditEventType.SCOPE_VIOLATION in event_types
        assert AuditEventType.EMERGENCY_STOP in event_types
        assert AuditEventType.HUMAN_INTERVENTION in event_types
        
        # Verify high severity events are marked appropriately
        for event in added_events:
            if event.event_type in [AuditEventType.SCOPE_VIOLATION, AuditEventType.EMERGENCY_STOP]:
                assert event.severity in ["high", "critical"]

    @pytest.mark.asyncio
    async def test_audit_log_session_correlation(
        self,
        audit_logger
    ):
        """Test audit log correlation across multiple sessions"""
        
        # Create multiple related sessions
        sessions = [
            {"session_id": f"session_{i}", "user_id": f"analyst_{i}"}
            for i in range(3)
        ]
        
        correlation_id = "engagement_PENTEST_2024_001"
        
        # Log events across multiple sessions with correlation
        for i, session in enumerate(sessions):
            await audit_logger.log_session_started(
                session_id=session["session_id"],
                user_id=session["user_id"],
                engagement_details={"engagement_id": "PENTEST_2024_001"},
                correlation_id=correlation_id
            )
            
            await audit_logger.log_action_executed(
                session_id=session["session_id"],
                action_id=f"action_{i}",
                execution_details={
                    "tool": "nmap",
                    "target": f"192.168.1.{100+i}"
                },
                correlation_id=correlation_id
            )
        
        # Verify session correlation
        assert audit_logger.db_session.add.call_count == 6  # 3 sessions × 2 events each
        
        added_events = [call.args[0] for call in audit_logger.db_session.add.call_args_list]
        
        # Verify all events have correct correlation ID
        for event in added_events:
            assert event.correlation_id == correlation_id
        
        # Verify events span multiple sessions
        session_ids = set(event.session_id for event in added_events)
        assert len(session_ids) == 3

    @pytest.mark.asyncio
    async def test_audit_log_retrieval_and_querying(
        self,
        audit_logger
    ):
        """Test audit log retrieval and querying capabilities"""
        
        # Mock database query results
        mock_audit_logs = [
            SecurityAuditLog(
                id=1,
                event_id="event_001",
                event_type=AuditEventType.SESSION_STARTED.value,
                session_id="test_session",
                timestamp=datetime.now(timezone.utc),
                context=json.dumps({"user_id": "analyst_1"}),
                integrity_hash="hash_001",
                severity="info"
            ),
            SecurityAuditLog(
                id=2,
                event_id="event_002",
                event_type=AuditEventType.FINDING_DISCOVERED.value,
                session_id="test_session",
                timestamp=datetime.now(timezone.utc),
                context=json.dumps({"finding_id": "CVE_2021_44228"}),
                integrity_hash="hash_002",
                severity="critical"
            )
        ]
        
        # Mock database query methods
        audit_logger.db_session.execute = AsyncMock()
        audit_logger.db_session.scalars = AsyncMock(return_value=Mock(all=Mock(return_value=mock_audit_logs)))
        
        # Test session-based audit log retrieval
        session_logs = await audit_logger.get_session_audit_logs("test_session")
        
        # Verify query execution
        assert audit_logger.db_session.scalars.called
        
        # Test critical finding retrieval
        critical_logs = await audit_logger.get_critical_audit_logs(
            start_time=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Verify critical log filtering would work
        assert audit_logger.db_session.scalars.called

    @pytest.mark.asyncio
    async def test_audit_log_performance_and_batching(
        self,
        audit_logger
    ):
        """Test audit logging performance with high volume events"""
        
        session_id = "performance_test_session"
        
        # Generate high volume of audit events
        audit_tasks = []
        for i in range(100):
            task = audit_logger.log_action_executed(
                session_id=session_id,
                action_id=f"action_{i:03d}",
                execution_details={
                    "tool": "nmap",
                    "target": f"192.168.1.{100 + (i % 155)}",  # Cycle through IP range
                    "port_count": i * 10,
                    "execution_time": i * 0.5
                }
            )
            audit_tasks.append(task)
        
        # Execute all audit events concurrently
        start_time = datetime.now(timezone.utc)
        await asyncio.gather(*audit_tasks)
        end_time = datetime.now(timezone.utc)
        
        execution_duration = (end_time - start_time).total_seconds()
        
        # Verify performance (all 100 events should complete within reasonable time)
        assert execution_duration < 5.0  # Should complete in under 5 seconds
        
        # Verify all events were logged
        assert audit_logger.db_session.add.call_count == 100
        assert audit_logger.db_session.commit.call_count == 100
        
        # Verify hash chain integrity maintained under load
        added_events = [call.args[0] for call in audit_logger.db_session.add.call_args_list]
        
        # Check that all events have valid hashes
        for event in added_events:
            assert event.integrity_hash is not None
            assert len(event.integrity_hash) > 0

    @pytest.mark.asyncio
    async def test_audit_log_tampering_detection(
        self,
        audit_logger
    ):
        """Test audit log tampering detection capabilities"""
        
        session_id = "tampering_test_session"
        
        # Create legitimate audit event
        event = await audit_logger.log_action_executed(
            session_id=session_id,
            action_id="legitimate_action",
            execution_details={"tool": "nmap", "target": "192.168.1.100"}
        )
        
        # Simulate tampering attempt by modifying event details
        original_hash = event.integrity_hash
        event.details["tool"] = "modified_tool"  # Simulate tampering
        
        # Verify tampering detection
        tampered_hash = audit_logger._calculate_event_hash(event)
        assert tampered_hash != original_hash
        
        # Test hash chain break detection
        event2 = await audit_logger.log_finding_discovered(
            session_id=session_id,
            finding={"finding_id": "test_finding"},
            previous_event=event
        )
        
        # If previous event was tampered, hash chain should be detectable
        assert event2.previous_hash == original_hash  # Should reference original, not tampered

if __name__ == "__main__":
    pytest.main([__file__, "-v"])