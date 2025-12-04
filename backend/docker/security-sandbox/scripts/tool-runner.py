#!/usr/bin/env python3
"""
MMCODE Security Tool Runner
===========================

Secure execution wrapper for security tools in Docker sandbox environment.

Features:
- Resource monitoring and enforcement
- Network access validation
- Tool execution timeout management
- Result collection and sanitization
- Audit logging for all operations
"""

import os
import sys
import json
import time
import signal
import asyncio
import logging
import subprocess
import resource
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import hashlib


# Configuration
SANDBOX_USER = os.environ.get('SANDBOX_USER', 'mmcode-runner')
MAX_SCAN_TIME = int(os.environ.get('MMCODE_MAX_SCAN_TIME', '3600'))
MAX_TARGETS = int(os.environ.get('MMCODE_MAX_TARGETS', '256'))
OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', '/tmp/scan-results'))
LOG_LEVEL = os.environ.get('MMCODE_LOG_LEVEL', 'INFO')

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / 'tool-runner.log')
    ]
)
logger = logging.getLogger('mmcode-tool-runner')


@dataclass
class ToolExecutionRequest:
    """Tool execution request structure"""
    tool_name: str
    target: str
    command_args: List[str]
    options: Dict[str, Any]
    timeout: int = MAX_SCAN_TIME
    session_id: str = ""
    request_id: str = ""
    authorized_by: str = ""


@dataclass
class ToolExecutionResult:
    """Tool execution result structure"""
    tool_name: str
    target: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    start_time: str
    end_time: str
    resource_usage: Dict[str, Any]
    output_files: List[str]
    findings_count: int
    session_id: str = ""
    request_id: str = ""


class SecuritySandboxRunner:
    """Main tool runner with security controls"""
    
    AUTHORIZED_TOOLS = {
        'nmap': {
            'binary': '/usr/bin/nmap',
            'max_args': 50,
            'allowed_args': [
                '-sV', '-sC', '-sS', '-sT', '-sU', '-sF', '-sX', '-sN',
                '-O', '-A', '-p', '-F', '--top-ports', '--version-all',
                '-oX', '-oN', '-oG', '--script', '--exclude'
            ],
            'blocked_args': [
                '--script=*dos*', '--script=*flood*', '--script=*brute*'
            ]
        },
        'nuclei': {
            'binary': '/usr/local/bin/nuclei',
            'max_args': 30,
            'allowed_args': [
                '-u', '-l', '-t', '-w', '-H', '-include-tags', '-exclude-tags',
                '-severity', '-author', '-o', '-json', '-irr', '-nc', '-r',
                '-c', '-rl', '-bs', '-stats'
            ],
            'blocked_args': [
                '-t', 'dos', '-t', 'fuzzing', '--dos', '--flood'
            ]
        },
        'masscan': {
            'binary': '/usr/bin/masscan',
            'max_args': 20,
            'allowed_args': [
                '-p', '--rate', '--range', '--exclude', '--excludefile',
                '-oX', '-oG', '-oJ', '--wait', '--retries'
            ],
            'blocked_args': [
                '--rate=*[5-9][0-9][0-9][0-9]*'  # Block rates > 5000
            ]
        }
    }
    
    def __init__(self):
        """Initialize sandbox runner"""
        self.start_time = time.time()
        self.resource_monitor = ResourceMonitor()
        self.network_validator = NetworkValidator()
        self.setup_resource_limits()
        self.setup_signal_handlers()
        
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / 'logs').mkdir(exist_ok=True)
        
        logger.info(f"MMCODE Security Sandbox Runner initialized")
        logger.info(f"Max scan time: {MAX_SCAN_TIME}s, Max targets: {MAX_TARGETS}")
    
    def setup_resource_limits(self):
        """Set resource limits for the process"""
        try:
            # CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, (MAX_SCAN_TIME, MAX_SCAN_TIME))
            
            # Memory limit (2GB soft, 2.5GB hard)
            memory_limit = 2 * 1024 * 1024 * 1024  # 2GB
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit + 512*1024*1024))
            
            # File descriptor limit
            resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 2048))
            
            # Process limit
            resource.setrlimit(resource.RLIMIT_NPROC, (50, 100))
            
            logger.info("Resource limits configured successfully")
            
        except Exception as e:
            logger.warning(f"Failed to set some resource limits: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.warning(f"Received signal {signum}, shutting down gracefully...")
            self.shutdown()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def validate_tool_request(self, request: ToolExecutionRequest) -> bool:
        """Validate tool execution request"""
        try:
            # Check if tool is authorized
            if request.tool_name not in self.AUTHORIZED_TOOLS:
                logger.error(f"Unauthorized tool: {request.tool_name}")
                return False
            
            tool_config = self.AUTHORIZED_TOOLS[request.tool_name]
            
            # Check argument count
            if len(request.command_args) > tool_config['max_args']:
                logger.error(f"Too many arguments for {request.tool_name}")
                return False
            
            # Validate arguments
            for arg in request.command_args:
                if arg not in tool_config['allowed_args']:
                    # Check if it's a parameter value (following an allowed arg)
                    continue
                
                # Check for blocked arguments
                for blocked in tool_config.get('blocked_args', []):
                    if blocked in arg or arg.startswith(blocked.split('=')[0]):
                        logger.error(f"Blocked argument detected: {arg}")
                        return False
            
            # Validate target
            if not self.network_validator.validate_target(request.target):
                logger.error(f"Invalid target: {request.target}")
                return False
            
            # Check timeout
            if request.timeout > MAX_SCAN_TIME:
                logger.error(f"Timeout too long: {request.timeout} > {MAX_SCAN_TIME}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute security tool with monitoring"""
        start_time = datetime.now(timezone.utc)
        execution_start = time.time()
        
        logger.info(f"Starting execution: {request.tool_name} -> {request.target}")
        
        # Validate request
        if not self.validate_tool_request(request):
            return ToolExecutionResult(
                tool_name=request.tool_name,
                target=request.target,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Request validation failed",
                execution_time=0.0,
                start_time=start_time.isoformat(),
                end_time=datetime.now(timezone.utc).isoformat(),
                resource_usage={},
                output_files=[],
                findings_count=0,
                session_id=request.session_id,
                request_id=request.request_id
            )
        
        tool_config = self.AUTHORIZED_TOOLS[request.tool_name]
        binary_path = tool_config['binary']
        
        # Build command
        cmd = [binary_path] + request.command_args
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(
            self.resource_monitor.monitor_execution(request.request_id)
        )
        
        try:
            # Execute command with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(OUTPUT_DIR),
                limit=1024*1024*50  # 50MB output limit
            )
            
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout
            )
            
            execution_end = time.time()
            end_time = datetime.now(timezone.utc)
            
            # Stop monitoring
            monitor_task.cancel()
            resource_usage = await self.resource_monitor.get_usage_stats(request.request_id)
            
            # Decode output
            stdout = stdout_data.decode('utf-8', errors='replace')
            stderr = stderr_data.decode('utf-8', errors='replace')
            
            # Find output files
            output_files = self.find_output_files(request.tool_name, request.target)
            
            # Count findings
            findings_count = self.count_findings(request.tool_name, stdout, output_files)
            
            result = ToolExecutionResult(
                tool_name=request.tool_name,
                target=request.target,
                success=(process.returncode == 0),
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_end - execution_start,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                resource_usage=resource_usage,
                output_files=output_files,
                findings_count=findings_count,
                session_id=request.session_id,
                request_id=request.request_id
            )
            
            # Log execution result
            self.log_execution_result(result)
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Tool execution timeout: {request.tool_name}")
            monitor_task.cancel()
            
            return ToolExecutionResult(
                tool_name=request.tool_name,
                target=request.target,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Execution timeout",
                execution_time=request.timeout,
                start_time=start_time.isoformat(),
                end_time=datetime.now(timezone.utc).isoformat(),
                resource_usage={},
                output_files=[],
                findings_count=0,
                session_id=request.session_id,
                request_id=request.request_id
            )
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            monitor_task.cancel()
            
            return ToolExecutionResult(
                tool_name=request.tool_name,
                target=request.target,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                execution_time=time.time() - execution_start,
                start_time=start_time.isoformat(),
                end_time=datetime.now(timezone.utc).isoformat(),
                resource_usage={},
                output_files=[],
                findings_count=0,
                session_id=request.session_id,
                request_id=request.request_id
            )
    
    def find_output_files(self, tool_name: str, target: str) -> List[str]:
        """Find output files generated by tool"""
        output_files = []
        patterns = [
            f"*{tool_name}*",
            f"*{target.replace('/', '_').replace(':', '_')}*",
            "*.xml", "*.json", "*.txt"
        ]
        
        for pattern in patterns:
            matching_files = list(OUTPUT_DIR.glob(pattern))
            output_files.extend([str(f) for f in matching_files])
        
        return list(set(output_files))  # Remove duplicates
    
    def count_findings(self, tool_name: str, stdout: str, output_files: List[str]) -> int:
        """Count findings from tool output"""
        findings_count = 0
        
        try:
            if tool_name == 'nmap':
                # Count open ports
                findings_count = stdout.count('open ')
            elif tool_name == 'nuclei':
                # Count vulnerabilities found
                findings_count = stdout.count('"template-id":')
            elif tool_name == 'masscan':
                # Count discovered ports
                findings_count = stdout.count('Discovered open port')
            
            # Also check output files for additional findings
            for file_path in output_files:
                if Path(file_path).exists():
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            if tool_name == 'nuclei' and file_path.endswith('.json'):
                                findings_count += content.count('"template-id":')
                    except Exception:
                        continue
        
        except Exception as e:
            logger.warning(f"Error counting findings: {e}")
        
        return findings_count
    
    def log_execution_result(self, result: ToolExecutionResult):
        """Log tool execution result"""
        log_file = OUTPUT_DIR / 'logs' / f"{result.tool_name}_execution.log"
        
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tool': result.tool_name,
            'target': result.target,
            'success': result.success,
            'exit_code': result.exit_code,
            'execution_time': result.execution_time,
            'findings_count': result.findings_count,
            'resource_usage': result.resource_usage,
            'session_id': result.session_id,
            'request_id': result.request_id
        }
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write execution log: {e}")
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down MMCODE Security Sandbox Runner")
        sys.exit(0)


class ResourceMonitor:
    """Monitor resource usage during tool execution"""
    
    def __init__(self):
        self.active_monitors = {}
    
    async def monitor_execution(self, request_id: str):
        """Monitor resource usage for a specific execution"""
        self.active_monitors[request_id] = {
            'start_time': time.time(),
            'cpu_usage': [],
            'memory_usage': [],
            'io_usage': []
        }
        
        try:
            while request_id in self.active_monitors:
                # Get current resource usage
                usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                
                self.active_monitors[request_id]['cpu_usage'].append(
                    usage.ru_utime + usage.ru_stime
                )
                self.active_monitors[request_id]['memory_usage'].append(
                    usage.ru_maxrss
                )
                
                await asyncio.sleep(1)  # Sample every second
                
        except asyncio.CancelledError:
            # Normal cancellation when execution completes
            pass
    
    async def get_usage_stats(self, request_id: str) -> Dict[str, Any]:
        """Get resource usage statistics"""
        if request_id not in self.active_monitors:
            return {}
        
        monitor_data = self.active_monitors.pop(request_id)
        
        return {
            'duration': time.time() - monitor_data['start_time'],
            'max_memory_kb': max(monitor_data['memory_usage']) if monitor_data['memory_usage'] else 0,
            'avg_memory_kb': sum(monitor_data['memory_usage']) / len(monitor_data['memory_usage']) if monitor_data['memory_usage'] else 0,
            'total_cpu_time': max(monitor_data['cpu_usage']) if monitor_data['cpu_usage'] else 0
        }


class NetworkValidator:
    """Validate network targets and access"""
    
    PRIVATE_RANGES = [
        '10.0.0.0/8',
        '172.16.0.0/12', 
        '192.168.0.0/16',
        '127.0.0.0/8'
    ]
    
    def __init__(self):
        self.allowed_ranges = self.PRIVATE_RANGES
    
    def validate_target(self, target: str) -> bool:
        """Validate if target is allowed"""
        import ipaddress
        
        try:
            # Extract IP from target (handle URLs, IP:port, etc.)
            ip_str = self.extract_ip(target)
            if not ip_str:
                return False
            
            ip = ipaddress.ip_address(ip_str)
            
            # Check if IP is in allowed ranges
            for range_str in self.allowed_ranges:
                if ip in ipaddress.ip_network(range_str, strict=False):
                    return True
            
            # Block public IPs by default
            logger.warning(f"Target IP {ip} not in allowed ranges")
            return False
            
        except Exception as e:
            logger.error(f"IP validation error for {target}: {e}")
            return False
    
    def extract_ip(self, target: str) -> Optional[str]:
        """Extract IP address from target string"""
        import re
        
        # Handle various target formats
        if target.startswith(('http://', 'https://')):
            # URL format
            from urllib.parse import urlparse
            parsed = urlparse(target)
            return parsed.hostname
        
        # IP:port format
        if ':' in target and not target.count(':') > 1:  # IPv4:port
            return target.split(':')[0]
        
        # Plain IP or hostname
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        match = re.search(ip_pattern, target)
        if match:
            return match.group(0)
        
        # Hostname - would need DNS resolution (not implemented for security)
        return None


def main():
    """Main entry point"""
    try:
        runner = SecuritySandboxRunner()
        logger.info("MMCODE Security Sandbox Runner started successfully")
        
        # Keep the container running and ready for requests
        # In production, this would listen for API requests
        while True:
            time.sleep(60)
            logger.debug("Sandbox runner heartbeat")
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()