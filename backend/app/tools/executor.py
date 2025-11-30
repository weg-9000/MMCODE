"""
Security Tool Executor
======================

Centralized executor for managing and coordinating security tool execution
with scope validation, rate limiting, and result aggregation.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Type
from datetime import datetime, timezone
from dataclasses import dataclass

from .base import BaseSecurityTool, ToolResult, ToolError
from .network import NmapTool, MasscanTool
from .vulnerability import NucleiTool, ZapTool
from .enumeration import GobusterTool, AmassTools
from ..security import SecurityAction, ScopeEnforcementEngine, SecurityAuditLogger

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRequest:
    """Request for tool execution"""
    tool_name: str
    target: str
    options: Dict[str, Any]
    phase: str
    priority: int = 5
    request_id: str = None
    
    def __post_init__(self):
        if not self.request_id:
            import uuid
            self.request_id = str(uuid.uuid4())


class SecurityToolExecutor:
    """
    Centralized security tool executor with scope validation and audit logging
    """
    
    # Registry of available tools
    AVAILABLE_TOOLS: Dict[str, Type[BaseSecurityTool]] = {
        'nmap': NmapTool,
        'masscan': MasscanTool,
        'nuclei': NucleiTool,
        'zap': ZapTool,
        'gobuster': GobusterTool,
        'amass': AmassTools
    }
    
    def __init__(self, 
                 scope_enforcer: ScopeEnforcementEngine,
                 audit_logger: SecurityAuditLogger,
                 max_concurrent_tools: int = 3,
                 default_timeout: int = 300):
        self.scope_enforcer = scope_enforcer
        self.audit_logger = audit_logger
        self.max_concurrent_tools = max_concurrent_tools
        self.default_timeout = default_timeout
        
        # Tool instances cache
        self._tool_instances: Dict[str, BaseSecurityTool] = {}
        
        # Execution tracking
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._execution_semaphore = asyncio.Semaphore(max_concurrent_tools)
        
        # Statistics
        self._execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'tools_used': {}
        }
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.AVAILABLE_TOOLS.keys())
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available"""
        return tool_name.lower() in self.AVAILABLE_TOOLS
    
    async def execute_tool(self, request: ExecutionRequest) -> ToolResult:
        """
        Execute a security tool with scope validation and audit logging
        
        Args:
            request: Execution request with tool, target, and options
            
        Returns:
            ToolResult with execution details and findings
        """
        tool_name = request.tool_name.lower()
        
        # Validate tool availability
        if not self.is_tool_available(tool_name):
            raise ToolError(f"Tool '{tool_name}' is not available")
        
        # Create security action for scope validation
        action = SecurityAction(
            action_id=f"tool_exec_{request.request_id}",
            action_type=f"execute_{tool_name}",
            target=request.target,
            tool_name=tool_name,
            phase=request.phase,
            risk_level=self._assess_tool_risk(tool_name, request.options)
        )
        
        # Validate against scope
        validation = await self.scope_enforcer.validate_action(action)
        if not validation.valid:
            await self.audit_logger.log_scope_validation(action, validation)
            raise ToolError(f"Tool execution blocked by scope validation: {validation.all_violations}")
        
        # Log execution start
        await self.audit_logger.log_action_execution(
            action=action,
            approval=None,  # Tools don't require approval by default
            status="started",
            result_details={
                "request_id": request.request_id,
                "options": request.options
            }
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get or create tool instance
            tool = await self._get_tool_instance(tool_name)
            
            # Execute with concurrency limiting
            async with self._execution_semaphore:
                self.logger.info(f"Executing {tool_name} against {request.target}")
                
                # Create execution task
                execution_task = asyncio.create_task(
                    tool.execute(request.target, request.options)
                )
                
                # Track active execution
                self._active_executions[request.request_id] = execution_task
                
                try:
                    result = await execution_task
                finally:
                    # Clean up tracking
                    if request.request_id in self._active_executions:
                        del self._active_executions[request.request_id]
            
            # Update statistics
            self._update_stats(tool_name, True)
            
            # Log successful execution
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            await self.audit_logger.log_action_execution(
                action=action,
                approval=None,
                status="completed",
                result_details={
                    "request_id": request.request_id,
                    "execution_time": execution_time,
                    "findings_count": len(result.findings),
                    "targets_discovered": len(result.targets_discovered),
                    "services_discovered": len(result.services_discovered)
                }
            )
            
            return result
            
        except Exception as e:
            # Update statistics
            self._update_stats(tool_name, False)
            
            # Log failed execution
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            await self.audit_logger.log_action_execution(
                action=action,
                approval=None,
                status="failed",
                result_details={
                    "request_id": request.request_id,
                    "execution_time": execution_time,
                    "error": str(e)
                }
            )
            
            self.logger.error(f"Tool execution failed: {tool_name} -> {request.target}: {e}")
            raise
    
    async def execute_multiple_tools(self, 
                                   requests: List[ExecutionRequest]) -> Dict[str, ToolResult]:
        """
        Execute multiple tools in parallel
        
        Args:
            requests: List of execution requests
            
        Returns:
            Dictionary mapping request IDs to results
        """
        self.logger.info(f"Executing {len(requests)} tool requests in parallel")
        
        # Create tasks for all requests
        tasks = []
        for request in requests:
            task = asyncio.create_task(
                self._execute_with_error_handling(request)
            )
            tasks.append((request.request_id, task))
        
        # Wait for all tasks to complete
        results = {}
        for request_id, task in tasks:
            try:
                result = await task
                results[request_id] = result
            except Exception as e:
                self.logger.error(f"Request {request_id} failed: {e}")
                # Store error result
                results[request_id] = ToolError(str(e))
        
        return results
    
    async def cancel_execution(self, request_id: str) -> bool:
        """
        Cancel an active tool execution
        
        Args:
            request_id: ID of the execution to cancel
            
        Returns:
            True if cancellation was successful
        """
        if request_id in self._active_executions:
            task = self._active_executions[request_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                self.logger.info(f"Successfully cancelled execution: {request_id}")
                return True
            except Exception as e:
                self.logger.warning(f"Error during cancellation of {request_id}: {e}")
                return False
        
        return False
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            **self._execution_stats,
            'active_executions': len(self._active_executions),
            'available_slots': self._execution_semaphore._value,
            'tool_instances': list(self._tool_instances.keys())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all available tools
        
        Returns:
            Health status for each tool
        """
        health_status = {}
        
        for tool_name in self.AVAILABLE_TOOLS:
            try:
                tool = await self._get_tool_instance(tool_name)
                # Basic health check - verify tool path exists
                health_status[tool_name] = {
                    'available': True,
                    'tool_path': tool.tool_path,
                    'last_check': datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                health_status[tool_name] = {
                    'available': False,
                    'error': str(e),
                    'last_check': datetime.now(timezone.utc).isoformat()
                }
        
        return health_status
    
    async def _get_tool_instance(self, tool_name: str) -> BaseSecurityTool:
        """Get or create tool instance"""
        if tool_name not in self._tool_instances:
            tool_class = self.AVAILABLE_TOOLS[tool_name]
            self._tool_instances[tool_name] = tool_class(
                timeout=self.default_timeout
            )
        
        return self._tool_instances[tool_name]
    
    def _assess_tool_risk(self, tool_name: str, options: Dict[str, Any]) -> str:
        """Assess risk level of tool execution"""
        from ..security.models import RiskLevel
        
        # Basic risk assessment based on tool type and options
        high_risk_tools = ['nuclei', 'zap']
        aggressive_options = ['aggressive', 'exploit', 'attack']
        
        if tool_name in high_risk_tools:
            return RiskLevel.MEDIUM
        
        # Check for aggressive options
        for option, value in options.items():
            if any(aggressive in str(value).lower() for aggressive in aggressive_options):
                return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _update_stats(self, tool_name: str, success: bool):
        """Update execution statistics"""
        self._execution_stats['total_executions'] += 1
        
        if success:
            self._execution_stats['successful_executions'] += 1
        else:
            self._execution_stats['failed_executions'] += 1
        
        # Tool-specific stats
        if tool_name not in self._execution_stats['tools_used']:
            self._execution_stats['tools_used'][tool_name] = {
                'total': 0,
                'success': 0,
                'failures': 0
            }
        
        tool_stats = self._execution_stats['tools_used'][tool_name]
        tool_stats['total'] += 1
        
        if success:
            tool_stats['success'] += 1
        else:
            tool_stats['failures'] += 1
    
    async def _execute_with_error_handling(self, request: ExecutionRequest) -> ToolResult:
        """Execute tool request with error handling"""
        try:
            return await self.execute_tool(request)
        except Exception as e:
            # Create error result
            return ToolResult(
                tool_name=request.tool_name,
                command=f"Failed to execute {request.tool_name}",
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=0.0,
                success=False,
                findings=[],
                targets_discovered=[],
                services_discovered=[]
            )