"""
Base Security Tool Interface
============================

Common interface for all security testing tools
"""

import asyncio
import logging
import shlex
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Base exception for tool execution errors"""
    def __init__(self, message: str, exit_code: int = None, stderr: str = None):
        self.message = message
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(message)


@dataclass
class ToolResult:
    """Standard result format for security tool execution"""
    tool_name: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    success: bool
    
    # Parsed results
    findings: List[Dict[str, Any]] = field(default_factory=list)
    targets_discovered: List[str] = field(default_factory=list)
    services_discovered: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    output_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            "tool_name": self.tool_name,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_time": self.execution_time,
            "success": self.success,
            "findings": self.findings,
            "targets_discovered": self.targets_discovered,
            "services_discovered": self.services_discovered,
            "timestamp": self.timestamp.isoformat(),
            "output_files": self.output_files
        }


class BaseSecurityTool(ABC):
    """
    Abstract base class for security tools integration
    """
    
    def __init__(self, 
                 tool_path: str = None,
                 timeout: int = 300,
                 output_dir: str = "/tmp/security_tools"):
        self.tool_path = tool_path or self.get_default_path()
        self.timeout = timeout
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Verify tool availability
        self._verify_tool_availability()
    
    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Tool name identifier"""
        pass
    
    @abstractmethod
    def get_default_path(self) -> str:
        """Get default installation path for the tool"""
        pass
    
    @abstractmethod
    def build_command(self, 
                     target: str, 
                     options: Dict[str, Any] = None) -> List[str]:
        """Build command arguments for tool execution"""
        pass
    
    @abstractmethod
    def parse_output(self, 
                    stdout: str, 
                    stderr: str, 
                    output_files: List[str] = None) -> List[Dict[str, Any]]:
        """Parse tool output into structured findings"""
        pass
    
    async def execute(self, 
                     target: str, 
                     options: Dict[str, Any] = None) -> ToolResult:
        """
        Execute security tool against target
        
        Args:
            target: Target to scan (IP, domain, URL)
            options: Tool-specific options
            
        Returns:
            ToolResult with execution details and findings
        """
        options = options or {}
        
        # Build command
        command_args = self.build_command(target, options)
        command_str = " ".join(shlex.quote(arg) for arg in command_args)
        
        self.logger.info(f"Executing {self.tool_name}: {command_str}")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *command_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.output_dir)
            )
            
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            stdout = stdout_data.decode('utf-8', errors='replace')
            stderr = stderr_data.decode('utf-8', errors='replace')
            exit_code = process.returncode
            
            # Find output files
            output_files = self._find_output_files(target, options)
            
            # Parse results
            findings = []
            if exit_code == 0 or self._is_partial_success(exit_code, stdout, stderr):
                try:
                    findings = self.parse_output(stdout, stderr, output_files)
                except Exception as e:
                    self.logger.warning(f"Failed to parse {self.tool_name} output: {e}")
            
            # Extract discovered targets and services
            targets_discovered = self._extract_targets(findings)
            services_discovered = self._extract_services(findings)
            
            return ToolResult(
                tool_name=self.tool_name,
                command=command_str,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                success=exit_code == 0,
                findings=findings,
                targets_discovered=targets_discovered,
                services_discovered=services_discovered,
                output_files=output_files
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            raise ToolError(
                f"{self.tool_name} execution timed out after {self.timeout}s",
                exit_code=124
            )
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            raise ToolError(f"{self.tool_name} execution failed: {str(e)}")
    
    def _verify_tool_availability(self) -> bool:
        """Verify that the tool is available and executable"""
        try:
            tool_path = Path(self.tool_path)
            if not tool_path.exists():
                raise ToolError(f"{self.tool_name} not found at {self.tool_path}")
            
            if not tool_path.is_file():
                raise ToolError(f"{self.tool_path} is not a file")
                
            # Try to execute with help/version flag
            return True
            
        except Exception as e:
            raise ToolError(f"{self.tool_name} verification failed: {str(e)}")
    
    def _is_partial_success(self, exit_code: int, stdout: str, stderr: str) -> bool:
        """Check if non-zero exit code should be treated as partial success"""
        # Override in subclasses for tool-specific logic
        return False
    
    def _find_output_files(self, 
                          target: str, 
                          options: Dict[str, Any]) -> List[str]:
        """Find output files generated by the tool"""
        output_files = []
        
        # Look for common output file patterns
        patterns = [
            f"*{target}*",
            f"*{self.tool_name}*",
            "*.xml",
            "*.json", 
            "*.txt",
            "*.csv"
        ]
        
        for pattern in patterns:
            matching_files = list(self.output_dir.glob(pattern))
            output_files.extend([str(f) for f in matching_files])
        
        return output_files
    
    def _extract_targets(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Extract discovered targets from findings"""
        targets = set()
        
        for finding in findings:
            if "target" in finding:
                targets.add(finding["target"])
            if "host" in finding:
                targets.add(finding["host"])
            if "ip" in finding:
                targets.add(finding["ip"])
        
        return list(targets)
    
    def _extract_services(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract discovered services from findings"""
        services = []
        
        for finding in findings:
            if finding.get("type") == "service":
                service_info = {
                    "host": finding.get("host"),
                    "port": finding.get("port"),
                    "protocol": finding.get("protocol"),
                    "service": finding.get("service"),
                    "version": finding.get("version"),
                    "state": finding.get("state", "open")
                }
                services.append(service_info)
        
        return services
    
    def sanitize_target(self, target: str) -> str:
        """Sanitize target input to prevent command injection"""
        # Basic sanitization - expand as needed
        import re
        
        # Allow only alphanumeric, dots, hyphens, colons, forward slashes
        if not re.match(r'^[a-zA-Z0-9\.\-\:/]+$', target):
            raise ToolError(f"Invalid target format: {target}")
        
        return target
    
    def get_output_filename(self, target: str, extension: str) -> str:
        """Generate safe output filename"""
        import re
        safe_target = re.sub(r'[^\w\.\-]', '_', target)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.tool_name}_{safe_target}_{timestamp}.{extension}"