"""
End-to-End Test: Approval Workflow Integration
==============================================

Test scenario: High-risk operation → approval request → approval processing → execution

This test validates the complete approval workflow including:
1. Risk assessment and approval requirement detection
2. Approval request creation and notification
3. Human approval processing with proper validation
4. Approved operation execution with proper tracking
5. Denial handling and rejection workflows
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.approval_integration import ApprovalIntegrationManager, ExecutionResult
from app.security.approval_workflow import ApprovalWorkflow, ApprovalRequest, ApprovalResult
from app.security.models import SecurityAction, generate_action_id, PentestPhase, RiskLevel
from app.security.notifications import NotificationManager
from app.tools.base import BaseSecurityTool, ToolResult
from app.models.models import HumanApproval, Session


class TestApprovalWorkflow:
    """E2E test suite for approval workflow integration"""

    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    async def mock_notification_manager(self):
        """Mock notification manager"""
        manager = Mock(spec=NotificationManager)
        manager.send_approval_request = AsyncMock()
        manager.send_approval_result = AsyncMock()
        return manager

    @pytest.fixture
    async def mock_security_tool(self):
        """Mock security tool for testing"""
        tool = Mock(spec=BaseSecurityTool)
        tool.tool_name = "test-exploit-tool"
        tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="test-exploit-tool",
            command="exploit-command target",
            exit_code=0,
            stdout="Exploit successful",
            stderr="",
            execution_time=5.2,
            success=True,
            findings=[{
                "type": "exploit_success",
                "target": "192.168.1.100",
                "payload": "reverse_shell",
                "impact": "system_compromise"
            }]
        ))
        return tool

    @pytest.fixture
    def high_risk_action(self):
        """Create high-risk security action requiring approval"""
        return SecurityAction(
            action_id=generate_action_id(),
            action_type="exploit_execution",
            target="192.168.1.100",
            tool_name="metasploit",
            method="reverse_shell",
            phase=PentestPhase.EXPLOITATION,
            risk_level=RiskLevel.HIGH,
            is_destructive=True,
            created_by="security_analyst_1"
        )

    @pytest.fixture
    def low_risk_action(self):
        """Create low-risk security action not requiring approval"""
        return SecurityAction(
            action_id=generate_action_id(),
            action_type="port_scan",
            target="192.168.1.100",
            tool_name="nmap",
            method="tcp_scan",
            phase=PentestPhase.SCANNING,
            risk_level=RiskLevel.LOW,
            is_destructive=False,
            created_by="security_analyst_1"
        )

    @pytest.mark.asyncio
    async def test_high_risk_approval_workflow_success(
        self, 
        mock_db_session, 
        mock_notification_manager, 
        mock_security_tool,
        high_risk_action
    ):
        """Test complete high-risk approval workflow with successful approval"""
        
        # Initialize approval integration manager
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Mock approval workflow behavior
        mock_approval_request = Mock(spec=ApprovalRequest)
        mock_approval_request.request_id = "approval_123"
        mock_approval_request.status = "pending"
        
        mock_approval_result = Mock(spec=ApprovalResult)
        mock_approval_result.approved = True
        mock_approval_result.approval_id = "approval_123"
        mock_approval_result.approved_by = "security_manager_1"
        mock_approval_result.decision_timestamp = datetime.now(timezone.utc)
        mock_approval_result.comments = "Approved for CVE testing"
        
        # Mock approval workflow methods
        approval_manager.approval_workflow.create_approval_request = AsyncMock(
            return_value=mock_approval_request
        )
        approval_manager.approval_workflow.wait_for_approval = AsyncMock(
            return_value=mock_approval_result
        )
        
        # Execute high-risk operation with approval
        result = await approval_manager.execute_with_approval(
            action=high_risk_action,
            tool_executor=mock_security_tool,
            session_id="test_session_1"
        )
        
        # Verify approval workflow was executed
        assert result.success is True
        assert result.status == "completed"
        assert result.approval_request_id is not None  # ID will be auto-generated
        assert len(result.findings) > 0
        assert result.execution_time > 0
        
        # Verify approval request was created
        approval_manager.approval_workflow.create_approval_request.assert_called_once()
        request_call_args = approval_manager.approval_workflow.create_approval_request.call_args[0][0]
        assert request_call_args.action_type == "exploit_execution"
        assert request_call_args.target == "192.168.1.100"
        assert request_call_args.risk_level == RiskLevel.HIGH
        
        # Verify approval was awaited
        approval_manager.approval_workflow.wait_for_approval.assert_called_once_with("approval_123")
        
        # Verify tool was executed after approval
        mock_security_tool.execute.assert_called_once_with(
            target="192.168.1.100",
            options={}
        )
        
        # Verify notifications were sent
        mock_notification_manager.send_approval_request.assert_called_once()
        mock_notification_manager.send_approval_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_high_risk_approval_workflow_denial(
        self,
        mock_db_session,
        mock_notification_manager,
        mock_security_tool,
        high_risk_action
    ):
        """Test high-risk approval workflow with denial"""
        
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Mock denial
        mock_approval_request = Mock(spec=ApprovalRequest)
        mock_approval_request.request_id = "approval_456"
        mock_approval_request.status = "pending"
        
        mock_approval_result = Mock(spec=ApprovalResult)
        mock_approval_result.approved = False
        mock_approval_result.approval_id = "approval_456"
        mock_approval_result.denied_by = "security_manager_2"
        mock_approval_result.decision_timestamp = datetime.now(timezone.utc)
        mock_approval_result.comments = "Insufficient justification for exploit execution"
        
        approval_manager.approval_workflow.create_approval_request = AsyncMock(
            return_value=mock_approval_request
        )
        approval_manager.approval_workflow.wait_for_approval = AsyncMock(
            return_value=mock_approval_result
        )
        
        # Execute operation that gets denied
        result = await approval_manager.execute_with_approval(
            action=high_risk_action,
            tool_executor=mock_security_tool,
            session_id="test_session_2"
        )
        
        # Verify denial handling
        assert result.success is False
        assert result.status == "denied"
        assert result.approval_request_id == "approval_456"
        assert len(result.findings) == 0  # Tool not executed
        assert "Insufficient justification" in result.message
        
        # Verify tool was NOT executed
        mock_security_tool.execute.assert_not_called()
        
        # Verify notification was sent
        mock_notification_manager.send_approval_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_low_risk_auto_approval_workflow(
        self,
        mock_db_session,
        mock_notification_manager,
        mock_security_tool,
        low_risk_action
    ):
        """Test low-risk operation with automatic approval"""
        
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Mock check_approval_required to return False for low-risk
        approval_manager.check_approval_required = AsyncMock(return_value=False)
        
        # Execute low-risk operation
        result = await approval_manager.execute_with_approval(
            action=low_risk_action,
            tool_executor=mock_security_tool,
            session_id="test_session_3"
        )
        
        # Verify auto-approval
        assert result.success is True
        assert result.status == "completed"
        assert result.approval_request_id is None  # No approval needed
        
        # Verify tool was executed immediately
        mock_security_tool.execute.assert_called_once()
        
        # Verify no approval workflow was triggered
        approval_manager.approval_workflow.create_approval_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_approval_timeout_handling(
        self,
        mock_db_session,
        mock_notification_manager,
        mock_security_tool,
        high_risk_action
    ):
        """Test approval timeout handling"""
        
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Mock approval request creation
        mock_approval_request = Mock(spec=ApprovalRequest)
        mock_approval_request.request_id = "approval_timeout_123"
        approval_manager.approval_workflow.create_approval_request = AsyncMock(
            return_value=mock_approval_request
        )
        
        # Mock timeout exception
        approval_manager.approval_workflow.wait_for_approval = AsyncMock(
            side_effect=asyncio.TimeoutError("Approval timeout")
        )
        
        # Execute operation with timeout
        result = await approval_manager.execute_with_approval(
            action=high_risk_action,
            tool_executor=mock_security_tool,
            session_id="test_session_timeout"
        )
        
        # Verify timeout handling
        assert result.success is False
        assert result.status == "timeout"
        assert "timeout" in result.message.lower()
        assert result.approval_request_id == "approval_timeout_123"
        
        # Verify tool was NOT executed
        mock_security_tool.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_approval_workflow_with_conditions(
        self,
        mock_db_session,
        mock_notification_manager,
        mock_security_tool,
        high_risk_action
    ):
        """Test approval workflow with conditional approval"""
        
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Mock conditional approval
        mock_approval_request = Mock(spec=ApprovalRequest)
        mock_approval_request.request_id = "approval_conditional_123"
        
        mock_approval_result = Mock(spec=ApprovalResult)
        mock_approval_result.approved = True
        mock_approval_result.approval_id = "approval_conditional_123"
        mock_approval_result.approved_by = "security_manager_1"
        mock_approval_result.decision_timestamp = datetime.now(timezone.utc)
        mock_approval_result.comments = "Approved with conditions"
        mock_approval_result.conditions = {
            "max_execution_time": 300,
            "require_monitoring": True,
            "restrict_payload": True
        }
        
        approval_manager.approval_workflow.create_approval_request = AsyncMock(
            return_value=mock_approval_request
        )
        approval_manager.approval_workflow.wait_for_approval = AsyncMock(
            return_value=mock_approval_result
        )
        
        # Execute with conditional approval
        result = await approval_manager.execute_with_approval(
            action=high_risk_action,
            tool_executor=mock_security_tool,
            session_id="test_session_conditional"
        )
        
        # Verify conditional approval handling
        assert result.success is True
        assert result.status == "completed"
        assert "conditions" in result.message.lower()
        
        # Verify tool execution with conditions applied
        mock_security_tool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_approval_workflow_error_handling(
        self,
        mock_db_session,
        mock_notification_manager,
        mock_security_tool,
        high_risk_action
    ):
        """Test approval workflow error handling"""
        
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Mock approval request creation failure
        approval_manager.approval_workflow.create_approval_request = AsyncMock(
            side_effect=Exception("Database connection error")
        )
        
        # Execute operation with error
        result = await approval_manager.execute_with_approval(
            action=high_risk_action,
            tool_executor=mock_security_tool,
            session_id="test_session_error"
        )
        
        # Verify error handling
        assert result.success is False
        assert result.status == "error"
        assert "error" in result.message.lower()
        assert result.error_details is not None
        
        # Verify tool was NOT executed
        mock_security_tool.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_approval_notification_failure_handling(
        self,
        mock_db_session,
        mock_security_tool,
        high_risk_action
    ):
        """Test graceful handling of notification failures"""
        
        # Create notification manager that fails
        mock_notification_manager = Mock(spec=NotificationManager)
        mock_notification_manager.send_approval_request = AsyncMock(
            side_effect=Exception("SMTP server unavailable")
        )
        mock_notification_manager.send_approval_result = AsyncMock()
        
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Mock successful approval despite notification failure
        mock_approval_request = Mock(spec=ApprovalRequest)
        mock_approval_request.request_id = "approval_notif_fail_123"
        
        mock_approval_result = Mock(spec=ApprovalResult)
        mock_approval_result.approved = True
        mock_approval_result.approval_id = "approval_notif_fail_123"
        
        approval_manager.approval_workflow.create_approval_request = AsyncMock(
            return_value=mock_approval_request
        )
        approval_manager.approval_workflow.wait_for_approval = AsyncMock(
            return_value=mock_approval_result
        )
        
        # Execute operation
        result = await approval_manager.execute_with_approval(
            action=high_risk_action,
            tool_executor=mock_security_tool,
            session_id="test_session_notif_fail"
        )
        
        # Verify approval workflow continues despite notification failure
        assert result.success is True
        assert result.status == "completed"
        
        # Verify tool was still executed
        mock_security_tool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_approval_workflows(
        self,
        mock_db_session,
        mock_notification_manager,
        mock_security_tool
    ):
        """Test handling of concurrent approval workflows"""
        
        approval_manager = ApprovalIntegrationManager(
            db_session=mock_db_session,
            notification_manager=mock_notification_manager
        )
        
        # Create multiple high-risk actions
        actions = [
            SecurityAction(
                action_id=generate_action_id(),
                action_type="exploit_execution",
                target=f"192.168.1.{100+i}",
                tool_name="metasploit",
                method="reverse_shell",
                phase=PentestPhase.EXPLOITATION,
                risk_level=RiskLevel.HIGH,
                is_destructive=True,
                created_by=f"analyst_{i}"
            )
            for i in range(3)
        ]
        
        # Mock approval workflow for concurrent requests
        approval_manager.approval_workflow.create_approval_request = AsyncMock(
            side_effect=[
                Mock(request_id=f"approval_concurrent_{i}")
                for i in range(3)
            ]
        )
        approval_manager.approval_workflow.wait_for_approval = AsyncMock(
            return_value=Mock(approved=True, approval_id="concurrent_approval")
        )
        
        # Execute concurrent approval workflows
        tasks = [
            approval_manager.execute_with_approval(
                action=action,
                tool_executor=mock_security_tool,
                session_id=f"session_{i}"
            )
            for i, action in enumerate(actions)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all workflows completed successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result.success is True
            assert result.status == "completed"
        
        # Verify all approval requests were created
        assert approval_manager.approval_workflow.create_approval_request.call_count == 3
        
        # Verify all tools were executed
        assert mock_security_tool.execute.call_count == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])