#!/usr/bin/env python3
"""
MMCODE Security Sandbox - Resource Monitor
==========================================

Resource monitoring and enforcement for the MMCODE security sandbox.
Monitors CPU, memory, disk, and network usage and enforces resource limits.

Version: 1.0.0
"""

import os
import sys
import time
import psutil
import signal
import threading
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limit configuration"""
    max_cpu_percent: float = 80.0          # Maximum CPU usage percentage
    max_memory_mb: int = 2048               # Maximum memory usage in MB
    max_disk_mb: int = 512                  # Maximum disk usage in MB
    max_processes: int = 100                # Maximum number of processes
    max_open_files: int = 1000              # Maximum open file descriptors
    max_execution_time: int = 3600          # Maximum execution time in seconds
    check_interval: int = 5                 # Monitoring interval in seconds
    warning_threshold: float = 0.8          # Warning threshold (80% of limit)


@dataclass
class ResourceUsage:
    """Current resource usage snapshot"""
    timestamp: str
    cpu_percent: float
    memory_mb: float
    disk_mb: float
    process_count: int
    open_files: int
    network_connections: int
    execution_time: float


class ResourceMonitor:
    """
    Resource monitoring and enforcement for security tool sandbox
    """
    
    def __init__(self, limits: ResourceLimits = None, output_dir: str = "/tmp"):
        """
        Initialize resource monitor
        
        Args:
            limits: Resource limits configuration
            output_dir: Directory for monitoring logs
        """
        self.limits = limits or ResourceLimits()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.start_time = time.time()
        self.monitoring = False
        self.monitor_thread = None
        self.usage_history: List[ResourceUsage] = []
        
        # Process tracking
        self.monitored_processes = set()
        self.process_tree_root = None
        
        # Alert tracking
        self.alert_count = 0
        self.last_alert_time = 0
        
        logger.info(f"Resource monitor initialized with limits: {asdict(self.limits)}")
    
    def start_monitoring(self, target_pid: int = None) -> bool:
        """
        Start resource monitoring
        
        Args:
            target_pid: PID to monitor (monitors all processes if None)
            
        Returns:
            True if monitoring started successfully
        """
        try:
            if self.monitoring:
                logger.warning("Resource monitoring already active")
                return True
            
            self.start_time = time.time()
            self.monitoring = True
            
            if target_pid:
                self.process_tree_root = psutil.Process(target_pid)
                logger.info(f"Monitoring process tree starting from PID {target_pid}")
            else:
                logger.info("Monitoring system-wide resources")
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info("Resource monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start resource monitoring: {str(e)}")
            return False
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """
        Stop resource monitoring and return summary
        
        Returns:
            Summary of monitoring session
        """
        if not self.monitoring:
            return {"error": "Monitoring not active"}
        
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        total_time = time.time() - self.start_time
        
        summary = {
            "total_monitoring_time": total_time,
            "total_alerts": self.alert_count,
            "usage_samples": len(self.usage_history),
            "limits": asdict(self.limits)
        }
        
        if self.usage_history:
            # Calculate statistics
            cpu_values = [u.cpu_percent for u in self.usage_history]
            memory_values = [u.memory_mb for u in self.usage_history]
            
            summary.update({
                "peak_cpu_percent": max(cpu_values),
                "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
                "peak_memory_mb": max(memory_values),
                "avg_memory_mb": sum(memory_values) / len(memory_values)
            })
        
        # Save monitoring log
        self._save_monitoring_log(summary)
        
        logger.info(f"Resource monitoring stopped. Summary: {summary}")
        return summary
    
    def get_current_usage(self) -> ResourceUsage:
        """
        Get current resource usage snapshot
        
        Returns:
            Current resource usage
        """
        try:
            # Get system-wide stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            
            # Get process-specific stats if monitoring specific process tree
            process_count = 0
            process_memory = 0
            open_files = 0
            
            if self.process_tree_root:
                try:
                    # Get all processes in the tree
                    processes = [self.process_tree_root]
                    processes.extend(self.process_tree_root.children(recursive=True))
                    
                    process_count = len(processes)
                    
                    for proc in processes:
                        try:
                            process_memory += proc.memory_info().rss
                            open_files += proc.num_fds() if hasattr(proc, 'num_fds') else 0
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process tree root no longer exists
                    self.process_tree_root = None
                    
            else:
                # System-wide process count
                process_count = len(psutil.pids())
                open_files = len(psutil.Process().open_files()) if hasattr(psutil.Process(), 'open_files') else 0
            
            # Network connections
            try:
                network_connections = len(psutil.net_connections())
            except (psutil.AccessDenied, AttributeError):
                network_connections = 0
            
            return ResourceUsage(
                timestamp=datetime.now(timezone.utc).isoformat(),
                cpu_percent=cpu_percent,
                memory_mb=memory_info.used / 1024 / 1024 if not self.process_tree_root else process_memory / 1024 / 1024,
                disk_mb=disk_info.used / 1024 / 1024,
                process_count=process_count,
                open_files=open_files,
                network_connections=network_connections,
                execution_time=time.time() - self.start_time
            )
            
        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return ResourceUsage(
                timestamp=datetime.now(timezone.utc).isoformat(),
                cpu_percent=0, memory_mb=0, disk_mb=0, process_count=0,
                open_files=0, network_connections=0, execution_time=0
            )
    
    def check_limits(self, usage: ResourceUsage) -> Tuple[bool, List[str]]:
        """
        Check if current usage exceeds limits
        
        Args:
            usage: Current resource usage
            
        Returns:
            Tuple of (within_limits, violations)
        """
        violations = []
        
        # CPU check
        if usage.cpu_percent > self.limits.max_cpu_percent:
            violations.append(f"CPU usage {usage.cpu_percent:.1f}% exceeds limit {self.limits.max_cpu_percent}%")
        
        # Memory check
        if usage.memory_mb > self.limits.max_memory_mb:
            violations.append(f"Memory usage {usage.memory_mb:.1f}MB exceeds limit {self.limits.max_memory_mb}MB")
        
        # Disk check  
        if usage.disk_mb > self.limits.max_disk_mb:
            violations.append(f"Disk usage {usage.disk_mb:.1f}MB exceeds limit {self.limits.max_disk_mb}MB")
        
        # Process count check
        if usage.process_count > self.limits.max_processes:
            violations.append(f"Process count {usage.process_count} exceeds limit {self.limits.max_processes}")
        
        # Open files check
        if usage.open_files > self.limits.max_open_files:
            violations.append(f"Open files {usage.open_files} exceeds limit {self.limits.max_open_files}")
        
        # Execution time check
        if usage.execution_time > self.limits.max_execution_time:
            violations.append(f"Execution time {usage.execution_time:.1f}s exceeds limit {self.limits.max_execution_time}s")
        
        return len(violations) == 0, violations
    
    def check_warnings(self, usage: ResourceUsage) -> List[str]:
        """
        Check if current usage is approaching limits (warning level)
        
        Args:
            usage: Current resource usage
            
        Returns:
            List of warning messages
        """
        warnings = []
        threshold = self.limits.warning_threshold
        
        if usage.cpu_percent > self.limits.max_cpu_percent * threshold:
            warnings.append(f"CPU usage {usage.cpu_percent:.1f}% approaching limit")
        
        if usage.memory_mb > self.limits.max_memory_mb * threshold:
            warnings.append(f"Memory usage {usage.memory_mb:.1f}MB approaching limit")
        
        if usage.process_count > self.limits.max_processes * threshold:
            warnings.append(f"Process count {usage.process_count} approaching limit")
        
        return warnings
    
    def terminate_monitored_processes(self) -> bool:
        """
        Terminate all monitored processes
        
        Returns:
            True if termination was successful
        """
        if not self.process_tree_root:
            logger.warning("No process tree to terminate")
            return True
        
        try:
            # Get all processes in the tree
            processes = [self.process_tree_root]
            processes.extend(self.process_tree_root.children(recursive=True))
            
            # Send SIGTERM first
            for proc in processes:
                try:
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Wait for graceful termination
            time.sleep(2)
            
            # Send SIGKILL if needed
            for proc in processes:
                try:
                    if proc.is_running():
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            logger.info("Monitored processes terminated")
            return True
            
        except Exception as e:
            logger.error(f"Error terminating processes: {str(e)}")
            return False
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in separate thread)"""
        logger.info("Resource monitoring loop started")
        
        while self.monitoring:
            try:
                # Get current usage
                usage = self.get_current_usage()
                self.usage_history.append(usage)
                
                # Check for limit violations
                within_limits, violations = self.check_limits(usage)
                
                if not within_limits:
                    self.alert_count += 1
                    current_time = time.time()
                    
                    # Rate limit alerts (max 1 per minute)
                    if current_time - self.last_alert_time > 60:
                        self.last_alert_time = current_time
                        logger.error(f"Resource limit violations detected: {violations}")
                        
                        # Terminate processes if resource limits exceeded
                        if self.process_tree_root:
                            logger.warning("Terminating monitored processes due to resource limit violations")
                            self.terminate_monitored_processes()
                            break
                
                # Check for warnings
                warnings = self.check_warnings(usage)
                if warnings:
                    for warning in warnings:
                        logger.warning(f"Resource warning: {warning}")
                
                # Limit history size
                if len(self.usage_history) > 1000:
                    self.usage_history = self.usage_history[-500:]
                
                # Sleep until next check
                time.sleep(self.limits.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(1)
        
        logger.info("Resource monitoring loop ended")
    
    def _save_monitoring_log(self, summary: Dict[str, Any]):
        """Save monitoring log to file"""
        try:
            log_file = self.output_dir / f"resource_monitor_{int(time.time())}.json"
            
            log_data = {
                "summary": summary,
                "usage_history": [asdict(u) for u in self.usage_history[-100:]]  # Last 100 samples
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            logger.info(f"Monitoring log saved to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save monitoring log: {str(e)}")


def main():
    """CLI interface for resource monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MMCODE Resource Monitor')
    parser.add_argument('--pid', type=int, help='Process ID to monitor')
    parser.add_argument('--max-cpu', type=float, default=80.0, help='Maximum CPU percentage')
    parser.add_argument('--max-memory', type=int, default=2048, help='Maximum memory in MB')
    parser.add_argument('--max-time', type=int, default=3600, help='Maximum execution time in seconds')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval in seconds')
    parser.add_argument('--output-dir', default='/tmp', help='Output directory for logs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create limits configuration
    limits = ResourceLimits(
        max_cpu_percent=args.max_cpu,
        max_memory_mb=args.max_memory,
        max_execution_time=args.max_time,
        check_interval=args.interval
    )
    
    # Create monitor
    monitor = ResourceMonitor(limits, args.output_dir)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, stopping monitor...")
        summary = monitor.stop_monitoring()
        print(f"Monitoring summary: {json.dumps(summary, indent=2)}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start monitoring
    if monitor.start_monitoring(args.pid):
        print("Resource monitoring started. Press Ctrl+C to stop.")
        
        try:
            # Keep main thread alive
            while monitor.monitoring:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        summary = monitor.stop_monitoring()
        print(f"Monitoring summary: {json.dumps(summary, indent=2)}")
    else:
        print("Failed to start resource monitoring")
        sys.exit(1)


if __name__ == "__main__":
    main()