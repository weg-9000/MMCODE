"""
Security API Endpoints
======================

FastAPI endpoints for the security platform functionality including:
- Penetration testing session management  
- Security tool execution
- Threat analysis and recommendations
- Finding and vulnerability management
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone

from ...agents import get_agent_manager
from ...security import (
    EngagementScope,
    SecurityAction, 
    SecurityFinding,
    PentestPhase,
    RiskLevel,
    SeverityLevel,
    HumanApproval,
    generate_action_id,
    generate_task_id
)
from ...tools import SecurityToolExecutor, ExecutionRequest
from ...models.models import (
    EngagementScope as EngagementScopeModel,
    PentestingSession,
    PentestingTask,
    SecurityFinding as SecurityFindingModel,
    SecurityAuditLog,
    HumanApproval as HumanApprovalModel,
    SeverityLevelEnum
)
from ...core.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["Security Platform"])


# Dependency to get tool executor
async def get_tool_executor() -> SecurityToolExecutor:
    """Get security tool executor instance"""
    agent_manager = get_agent_manager()
    return SecurityToolExecutor(
        scope_enforcer=agent_manager.scope_enforcer,
        audit_logger=agent_manager.audit_logger
    )


@router.get("/health", summary="Security platform health check")
async def security_health_check():
    """Check health status of security platform components"""
    try:
        agent_manager = get_agent_manager()
        tool_executor = await get_tool_executor()
        
        # Check components
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "threat_analyzer": {
                    "available": True,
                    "stats": agent_manager.threat_analyzer.get_stats()
                },
                "scope_enforcer": {
                    "available": True,
                    "validation_engine": "active"
                },
                "audit_logger": {
                    "available": True,
                    "logging": "active"
                },
                "security_tools": await tool_executor.health_check()
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# Engagement Scope Management

@router.post("/scopes", summary="Create engagement scope")
async def create_engagement_scope(
    scope_data: Dict[str, Any],
    db = Depends(get_db)
):
    """Create a new security engagement scope"""
    try:
        # Create engagement scope object
        scope = EngagementScope(
            engagement_name=scope_data["engagement_name"],
            description=scope_data.get("description"),
            domains=scope_data.get("domains", []),
            ip_ranges=scope_data.get("ip_ranges", []),
            excluded_ips=scope_data.get("excluded_ips", []),
            allowed_ports=scope_data.get("allowed_ports", []),
            testing_window_start=scope_data.get("testing_window_start"),
            testing_window_end=scope_data.get("testing_window_end"),
            max_concurrent_scans=scope_data.get("max_concurrent_scans", 5),
            rate_limit_per_second=scope_data.get("rate_limit_per_second", 10),
            authorized_by=scope_data.get("authorized_by"),
            authorization_document=scope_data.get("authorization_document")
        )
        
        # Create database model
        db_scope = EngagementScopeModel(
            engagement_name=scope.engagement_name,
            description=scope.description,
            domains=scope.domains,
            ip_ranges=scope.ip_ranges,
            excluded_ips=scope.excluded_ips,
            allowed_ports=scope.allowed_ports,
            testing_window_start=scope.testing_window_start,
            testing_window_end=scope.testing_window_end,
            max_concurrent_scans=scope.max_concurrent_scans,
            rate_limit_per_second=scope.rate_limit_per_second,
            authorized_by=scope.authorized_by,
            authorization_document=scope.authorization_document
        )
        
        db.add(db_scope)
        db.commit()
        db.refresh(db_scope)
        
        return {
            "scope_id": db_scope.id,
            "engagement_name": db_scope.engagement_name,
            "status": "created",
            "message": "Engagement scope created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create engagement scope: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create engagement scope: {str(e)}"
        )


@router.get("/scopes", summary="List engagement scopes")
async def list_engagement_scopes(db = Depends(get_db)):
    """List all engagement scopes"""
    try:
        scopes = db.query(EngagementScopeModel).all()
        
        return {
            "scopes": [
                {
                    "id": scope.id,
                    "engagement_name": scope.engagement_name,
                    "description": scope.description,
                    "domains": scope.domains,
                    "ip_ranges": scope.ip_ranges,
                    "authorized_by": scope.authorized_by,
                    "created_at": scope.created_at.isoformat()
                }
                for scope in scopes
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list engagement scopes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list engagement scopes: {str(e)}"
        )


# Penetration Testing Session Management

@router.post("/sessions", summary="Start penetration testing session")
async def start_pentest_session(
    session_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db = Depends(get_db)
):
    """Start a new penetration testing session"""
    try:
        # Get scope
        scope = db.query(EngagementScopeModel).filter(
            EngagementScopeModel.id == session_data["scope_id"]
        ).first()
        
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement scope not found"
            )
        
        # Convert to security scope object
        security_scope = EngagementScope(
            engagement_name=scope.engagement_name,
            description=scope.description,
            domains=scope.domains,
            ip_ranges=scope.ip_ranges,
            excluded_ips=scope.excluded_ips,
            allowed_ports=scope.allowed_ports,
            testing_window_start=scope.testing_window_start,
            testing_window_end=scope.testing_window_end,
            max_concurrent_scans=scope.max_concurrent_scans,
            rate_limit_per_second=scope.rate_limit_per_second,
            authorized_by=scope.authorized_by,
            authorization_document=scope.authorization_document
        )
        
        # Start threat analysis session
        agent_manager = get_agent_manager()
        objectives = session_data.get("objectives", ["Comprehensive security assessment"])
        
        # Initialize PTT
        result = await agent_manager.analyze_security_threats(security_scope, objectives)
        
        # Create database session
        db_session = PentestingSession(
            scope_id=scope.id,
            session_name=session_data["session_name"],
            objectives=objectives,
            tree_id=result["tree_id"],
            primary_target=result["target"],
            estimated_duration_hours=session_data.get("estimated_duration_hours", 24)
        )
        
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return {
            "session_id": db_session.id,
            "session_name": db_session.session_name,
            "tree_id": db_session.tree_id,
            "primary_target": db_session.primary_target,
            "current_phase": db_session.current_phase.value,
            "status": "active",
            "message": "Penetration testing session started successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to start pentest session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start pentest session: {str(e)}"
        )


@router.get("/sessions/{session_id}", summary="Get session details")
async def get_session_details(session_id: str, db = Depends(get_db)):
    """Get detailed information about a penetration testing session"""
    try:
        session = db.query(PentestingSession).filter(
            PentestingSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get associated data
        tasks = db.query(PentestingTask).filter(
            PentestingTask.session_id == session_id
        ).all()
        
        findings = db.query(SecurityFindingModel).filter(
            SecurityFindingModel.session_id == session_id
        ).all()
        
        return {
            "session": {
                "id": session.id,
                "session_name": session.session_name,
                "objectives": session.objectives,
                "current_phase": session.current_phase.value,
                "status": session.status,
                "tree_id": session.tree_id,
                "primary_target": session.primary_target,
                "started_at": session.started_at.isoformat(),
                "tasks_completed": session.tasks_completed,
                "findings_count": session.findings_count,
                "critical_findings_count": session.critical_findings_count
            },
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "phase": task.phase.value,
                    "status": task.status,
                    "priority_score": task.priority_score,
                    "risk_level": task.risk_level.value,
                    "requires_approval": task.requires_approval
                }
                for task in tasks
            ],
            "findings": [
                {
                    "id": finding.id,
                    "title": finding.title,
                    "severity": finding.severity.value,
                    "category": finding.category,
                    "affected_component": finding.affected_component,
                    "status": finding.status,
                    "created_at": finding.created_at.isoformat()
                }
                for finding in findings
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get session details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session details: {str(e)}"
        )


# Task and Recommendation Management

@router.get("/sessions/{session_id}/recommendations", summary="Get next task recommendations")
async def get_task_recommendations(session_id: str):
    """Get next task recommendations for a penetration testing session"""
    try:
        agent_manager = get_agent_manager()
        recommendation = await agent_manager.get_security_recommendation()
        
        return {
            "session_id": session_id,
            "recommendation": recommendation,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get task recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task recommendations: {str(e)}"
        )


@router.post("/sessions/{session_id}/execute-task", summary="Execute approved task")
async def execute_approved_task(
    session_id: str,
    task_data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Execute an approved penetration testing task"""
    try:
        # Create approval object
        approval = HumanApproval(
            action_id=task_data["task_id"],
            action_description=task_data.get("description", "Manual task execution"),
            risk_level=RiskLevel[task_data.get("risk_level", "LOW")],
            approver_name=task_data["approver_name"],
            approver_email=task_data.get("approver_email"),
            approved=True,
            approval_comments=task_data.get("comments"),
            approved_at=datetime.now(timezone.utc),
            expires_at=task_data.get("expires_at")
        )
        
        # Get agent manager and execute task
        agent_manager = get_agent_manager()
        
        # This is a simplified execution - in practice, you'd need to reconstruct
        # the TaskNode object from the database
        result = await agent_manager.execute_security_task(
            task=None,  # Would need to reconstruct from DB
            approval=approval
        )
        
        return {
            "session_id": session_id,
            "task_id": task_data["task_id"],
            "execution_result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to execute task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute task: {str(e)}"
        )


# Security Tool Execution

@router.get("/tools", summary="List available security tools")
async def list_security_tools():
    """Get list of available security tools"""
    try:
        tool_executor = await get_tool_executor()
        
        return {
            "available_tools": tool_executor.get_available_tools(),
            "execution_stats": tool_executor.get_execution_stats(),
            "tool_health": await tool_executor.health_check()
        }
        
    except Exception as e:
        logger.error(f"Failed to list security tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list security tools: {str(e)}"
        )


@router.post("/tools/execute", summary="Execute security tool")
async def execute_security_tool(
    tool_request: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Execute a security tool against a target"""
    try:
        # Create execution request
        request = ExecutionRequest(
            tool_name=tool_request["tool_name"],
            target=tool_request["target"],
            options=tool_request.get("options", {}),
            phase=tool_request.get("phase", "manual"),
            priority=tool_request.get("priority", 5)
        )
        
        # Execute tool
        tool_executor = await get_tool_executor()
        result = await tool_executor.execute_tool(request)
        
        return {
            "request_id": request.request_id,
            "tool_name": result.tool_name,
            "target": request.target,
            "execution_time": result.execution_time,
            "success": result.success,
            "findings_count": len(result.findings),
            "targets_discovered": len(result.targets_discovered),
            "services_discovered": len(result.services_discovered),
            "output_files": result.output_files,
            "timestamp": result.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to execute security tool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute security tool: {str(e)}"
        )


# Finding Management

@router.get("/findings", summary="List security findings")
async def list_security_findings(
    session_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db = Depends(get_db)
):
    """List security findings with optional filtering"""
    try:
        query = db.query(SecurityFindingModel)
        
        # Apply filters
        if session_id:
            query = query.filter(SecurityFindingModel.session_id == session_id)
        
        if severity:
            query = query.filter(SecurityFindingModel.severity == severity)
        
        if status:
            query = query.filter(SecurityFindingModel.status == status)
        
        findings = query.limit(limit).all()
        
        return {
            "findings": [
                {
                    "id": finding.id,
                    "title": finding.title,
                    "description": finding.description,
                    "severity": finding.severity.value,
                    "category": finding.category,
                    "affected_component": finding.affected_component,
                    "service_name": finding.service_name,
                    "port_number": finding.port_number,
                    "cve_id": finding.cve_id,
                    "cvss_score": finding.cvss_score,
                    "status": finding.status,
                    "created_at": finding.created_at.isoformat()
                }
                for finding in findings
            ],
            "total_count": len(findings)
        }
        
    except Exception as e:
        logger.error(f"Failed to list security findings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list security findings: {str(e)}"
        )


@router.get("/findings/{finding_id}", summary="Get finding details")
async def get_finding_details(finding_id: str, db = Depends(get_db)):
    """Get detailed information about a specific finding"""
    try:
        finding = db.query(SecurityFindingModel).filter(
            SecurityFindingModel.id == finding_id
        ).first()
        
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding not found"
            )
        
        return {
            "id": finding.id,
            "title": finding.title,
            "description": finding.description,
            "severity": finding.severity.value,
            "confidence": finding.confidence,
            "category": finding.category,
            "affected_component": finding.affected_component,
            "service_name": finding.service_name,
            "port_number": finding.port_number,
            "protocol": finding.protocol,
            "cve_id": finding.cve_id,
            "cvss_score": finding.cvss_score,
            "cvss_vector": finding.cvss_vector,
            "exploit_available": finding.exploit_available,
            "evidence_data": finding.evidence_data,
            "proof_of_concept": finding.proof_of_concept,
            "impact": finding.impact,
            "remediation": finding.remediation,
            "references": finding.references,
            "status": finding.status,
            "created_at": finding.created_at.isoformat(),
            "updated_at": finding.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get finding details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get finding details: {str(e)}"
        )


# Audit and Compliance

@router.get("/audit-logs", summary="Get audit logs") 
async def get_audit_logs(
    session_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db = Depends(get_db)
):
    """Get audit logs with optional filtering"""
    try:
        query = db.query(SecurityAuditLog)
        
        # Apply filters
        if session_id:
            query = query.filter(SecurityAuditLog.session_id == session_id)
        
        if event_type:
            query = query.filter(SecurityAuditLog.event_type == event_type)
        
        if severity:
            query = query.filter(SecurityAuditLog.severity == severity)
        
        # Order by timestamp descending
        logs = query.order_by(SecurityAuditLog.timestamp.desc()).limit(limit).all()
        
        return {
            "audit_logs": [
                {
                    "id": log.id,
                    "event_type": log.event_type,
                    "event_category": log.event_category,
                    "severity": log.severity,
                    "actor_type": log.actor_type,
                    "actor_id": log.actor_id,
                    "action_id": log.action_id,
                    "action_type": log.action_type,
                    "target": log.target,
                    "tool_name": log.tool_name,
                    "timestamp": log.timestamp.isoformat()
                }
                for log in logs
            ],
            "total_count": len(logs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}"
        )


# Statistics and Reporting

@router.get("/stats", summary="Get security platform statistics")
async def get_security_stats(db = Depends(get_db)):
    """Get comprehensive security platform statistics"""
    try:
        # Query statistics from database
        total_sessions = db.query(PentestingSession).count()
        active_sessions = db.query(PentestingSession).filter(
            PentestingSession.status == "active"
        ).count()
        
        total_findings = db.query(SecurityFindingModel).count()
        critical_findings = db.query(SecurityFindingModel).filter(
            SecurityFindingModel.severity == SeverityLevelEnum.CRITICAL
        ).count()
        high_findings = db.query(SecurityFindingModel).filter(
            SecurityFindingModel.severity == SeverityLevelEnum.HIGH
        ).count()
        
        # Get tool executor stats
        tool_executor = await get_tool_executor()
        tool_stats = tool_executor.get_execution_stats()
        
        # Get agent stats
        agent_manager = get_agent_manager()
        agent_stats = agent_manager.threat_analyzer.get_stats()
        
        return {
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
                "completed": total_sessions - active_sessions
            },
            "findings": {
                "total": total_findings,
                "critical": critical_findings,
                "high": high_findings,
                "medium_low": total_findings - critical_findings - high_findings
            },
            "tools": tool_stats,
            "threat_analyzer": agent_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get security stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security stats: {str(e)}"
        )