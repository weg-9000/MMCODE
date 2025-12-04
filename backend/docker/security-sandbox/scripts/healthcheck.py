#!/usr/bin/env python3
"""
MMCODE Security Sandbox Health Check
====================================

Health check script for Docker container to verify:
- System resources availability
- Security tool accessibility
- Network configuration
- File system permissions
- Service readiness
"""

import os
import sys
import json
import time
import subprocess
import resource
from pathlib import Path
from datetime import datetime, timezone


class HealthChecker:
    """Comprehensive health check for security sandbox"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_total = 0
        self.results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'unknown',
            'checks': {}
        }
    
    def run_check(self, name: str, check_func, critical: bool = True):
        """Run individual health check"""
        self.checks_total += 1
        
        try:
            start_time = time.time()
            result = check_func()
            duration = time.time() - start_time
            
            self.results['checks'][name] = {
                'status': 'pass' if result else 'fail',
                'critical': critical,
                'duration_ms': round(duration * 1000, 2),
                'message': getattr(check_func, '__doc__', 'No description')
            }
            
            if result:
                self.checks_passed += 1
                print(f"✓ {name}")
            else:
                status = "CRITICAL" if critical else "WARNING"
                print(f"✗ {name} [{status}]")
                
        except Exception as e:
            self.results['checks'][name] = {
                'status': 'error',
                'critical': critical,
                'duration_ms': 0,
                'error': str(e)
            }
            print(f"✗ {name} [ERROR: {e}]")
    
    def check_user_permissions(self):
        """Verify running as non-root user with proper permissions"""
        try:
            # Check not running as root
            if os.getuid() == 0:
                return False
            
            # Check user matches expected sandbox user
            expected_user = os.environ.get('SANDBOX_USER', 'mmcode-runner')
            import pwd
            current_user = pwd.getpwuid(os.getuid()).pw_name
            
            if current_user != expected_user:
                return False
            
            # Check output directory permissions
            output_dir = Path(os.environ.get('OUTPUT_DIR', '/tmp/scan-results'))
            if not output_dir.exists() or not os.access(output_dir, os.W_OK):
                return False
            
            return True
            
        except Exception:
            return False
    
    def check_security_tools_availability(self):
        """Verify security tools are installed and accessible"""
        tools = {
            'nmap': '/usr/bin/nmap',
            'nuclei': '/usr/local/bin/nuclei',
            'masscan': '/usr/bin/masscan'
        }
        
        for tool_name, tool_path in tools.items():
            try:
                if not Path(tool_path).exists():
                    print(f"  Missing tool: {tool_name} at {tool_path}")
                    return False
                
                if not os.access(tool_path, os.X_OK):
                    print(f"  Tool not executable: {tool_name}")
                    return False
                
                # Test tool execution
                result = subprocess.run(
                    [tool_path, '--version'],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"  Tool version check failed: {tool_name}")
                    return False
                
            except Exception as e:
                print(f"  Tool check error for {tool_name}: {e}")
                return False
        
        return True
    
    def check_resource_limits(self):
        """Verify resource limits are properly configured"""
        try:
            # Check CPU limit
            cpu_limit = resource.getrlimit(resource.RLIMIT_CPU)
            if cpu_limit[0] <= 0:
                return False
            
            # Check memory limit
            memory_limit = resource.getrlimit(resource.RLIMIT_AS)
            if memory_limit[0] <= 0:
                return False
            
            # Check file descriptor limit
            fd_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            if fd_limit[0] <= 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def check_nuclei_templates(self):
        """Verify Nuclei templates are available"""
        try:
            templates_dir = Path(os.environ.get('NUCLEI_TEMPLATES_DIR', '/home/mmcode-runner/nuclei-templates'))
            
            if not templates_dir.exists():
                return False
            
            # Check for key template directories
            required_dirs = ['cves', 'technologies', 'vulnerabilities']
            for dir_name in required_dirs:
                if not (templates_dir / dir_name).exists():
                    print(f"  Missing template directory: {dir_name}")
                    return False
            
            # Count available templates
            template_count = len(list(templates_dir.rglob('*.yaml')))
            if template_count < 100:  # Minimum expected templates
                print(f"  Insufficient templates: {template_count}")
                return False
            
            return True
            
        except Exception:
            return False
    
    def check_network_configuration(self):
        """Verify network configuration and restrictions"""
        try:
            # Test internal network connectivity
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', '127.0.0.1'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False
            
            # Verify external network is properly restricted
            # This should fail in a properly configured sandbox
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                capture_output=True,
                timeout=5
            )
            
            # If external ping succeeds, network isolation may not be working
            # This is a warning rather than failure for some configurations
            if result.returncode == 0:
                print("  Warning: External network access detected")
            
            return True
            
        except Exception:
            return False
    
    def check_file_system_security(self):
        """Verify file system security settings"""
        try:
            # Check if root filesystem is read-only (in production)
            with open('/proc/mounts', 'r') as f:
                mounts = f.read()
            
            # Check for proper tmp mount with security options
            tmp_found = False
            for line in mounts.split('\n'):
                if '/tmp' in line and 'tmpfs' in line:
                    tmp_found = True
                    if 'noexec' not in line or 'nosuid' not in line:
                        print("  /tmp mount missing security options")
                        return False
            
            if not tmp_found:
                print("  /tmp tmpfs mount not found")
                # Don't fail for this in development environments
            
            # Check output directory permissions
            output_dir = Path(os.environ.get('OUTPUT_DIR', '/tmp/scan-results'))
            stat_info = output_dir.stat()
            
            # Verify directory is writable by current user
            if not os.access(output_dir, os.W_OK):
                return False
            
            return True
            
        except Exception:
            return False
    
    def check_process_limits(self):
        """Verify process and resource limits"""
        try:
            # Check process count limit
            proc_limit = resource.getrlimit(resource.RLIMIT_NPROC)
            if proc_limit[0] <= 0 or proc_limit[0] > 1000:  # Reasonable limit
                print(f"  Process limit seems wrong: {proc_limit[0]}")
                return False
            
            # Check current resource usage
            usage = resource.getrusage(resource.RUSAGE_SELF)
            
            # Memory usage should be reasonable
            if usage.ru_maxrss > 500 * 1024:  # 500MB in KB
                print(f"  High memory usage: {usage.ru_maxrss} KB")
                # Don't fail, just warn
            
            return True
            
        except Exception:
            return False
    
    def check_configuration_files(self):
        """Verify configuration files are accessible"""
        try:
            config_dir = Path(os.environ.get('CONFIG_DIR', '/etc/mmcode-sandbox'))
            
            if not config_dir.exists():
                print(f"  Config directory not found: {config_dir}")
                return False
            
            # Check key configuration files
            required_configs = ['nmap', 'nuclei']
            for config_name in required_configs:
                config_path = config_dir / config_name
                if not config_path.exists():
                    print(f"  Missing config: {config_name}")
                    continue  # Don't fail for missing configs in development
            
            return True
            
        except Exception:
            return False
    
    def check_logging_capability(self):
        """Verify logging is working properly"""
        try:
            output_dir = Path(os.environ.get('OUTPUT_DIR', '/tmp/scan-results'))
            log_dir = output_dir / 'logs'
            
            # Create log directory if it doesn't exist
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Test log writing
            test_log = log_dir / 'healthcheck_test.log'
            test_content = f"Health check test - {datetime.now(timezone.utc).isoformat()}"
            
            with open(test_log, 'w') as f:
                f.write(test_content)
            
            # Verify log was written
            if not test_log.exists():
                return False
            
            with open(test_log, 'r') as f:
                if f.read().strip() != test_content:
                    return False
            
            # Clean up test file
            test_log.unlink()
            
            return True
            
        except Exception as e:
            print(f"  Logging test error: {e}")
            return False
    
    def run_all_checks(self):
        """Run all health checks"""
        print("MMCODE Security Sandbox Health Check")
        print("=" * 40)
        
        # Critical checks (must pass)
        self.run_check("User Permissions", self.check_user_permissions, critical=True)
        self.run_check("Security Tools", self.check_security_tools_availability, critical=True)
        self.run_check("Resource Limits", self.check_resource_limits, critical=True)
        self.run_check("File System Security", self.check_file_system_security, critical=True)
        self.run_check("Logging Capability", self.check_logging_capability, critical=True)
        
        # Important checks (warnings if failed)
        self.run_check("Nuclei Templates", self.check_nuclei_templates, critical=False)
        self.run_check("Network Configuration", self.check_network_configuration, critical=False)
        self.run_check("Process Limits", self.check_process_limits, critical=False)
        self.run_check("Configuration Files", self.check_configuration_files, critical=False)
        
        # Determine overall status
        critical_failures = sum(
            1 for check in self.results['checks'].values()
            if check['critical'] and check['status'] != 'pass'
        )
        
        if critical_failures > 0:
            self.results['overall_status'] = 'unhealthy'
        elif self.checks_passed == self.checks_total:
            self.results['overall_status'] = 'healthy'
        else:
            self.results['overall_status'] = 'degraded'
        
        # Print summary
        print("\n" + "=" * 40)
        print(f"Health Check Summary: {self.results['overall_status'].upper()}")
        print(f"Checks Passed: {self.checks_passed}/{self.checks_total}")
        
        if critical_failures > 0:
            print(f"Critical Failures: {critical_failures}")
        
        # Write detailed results to file
        try:
            output_dir = Path(os.environ.get('OUTPUT_DIR', '/tmp/scan-results'))
            health_file = output_dir / 'healthcheck_result.json'
            with open(health_file, 'w') as f:
                json.dump(self.results, f, indent=2)
        except Exception as e:
            print(f"Failed to write health check results: {e}")
        
        # Exit with appropriate code
        if self.results['overall_status'] == 'unhealthy':
            sys.exit(1)
        elif self.results['overall_status'] == 'degraded':
            sys.exit(2)  # Warning exit code
        else:
            sys.exit(0)  # Healthy


def main():
    """Main entry point"""
    try:
        checker = HealthChecker()
        checker.run_all_checks()
    except KeyboardInterrupt:
        print("\nHealth check interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"Health check failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()