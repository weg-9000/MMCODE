#!/usr/bin/env python3
"""
MMCODE Security Sandbox - Network Validator
===========================================

Network validation and security enforcement for the MMCODE security sandbox.
Validates network targets and enforces security policies before tool execution.

Version: 1.0.0
"""

import re
import ipaddress
import socket
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class NetworkPolicy:
    """Network access policy definition"""
    allowed_private_ranges: List[str] = None
    blocked_public_ranges: List[str] = None
    allowed_ports: List[int] = None
    blocked_ports: List[int] = None
    max_targets: int = 1000
    dns_allowed: bool = True
    
    def __post_init__(self):
        if self.allowed_private_ranges is None:
            self.allowed_private_ranges = [
                "10.0.0.0/8",
                "172.16.0.0/12", 
                "192.168.0.0/16"
            ]
        
        if self.blocked_public_ranges is None:
            self.blocked_public_ranges = [
                "0.0.0.0/8",      # This network
                "127.0.0.0/8",    # Loopback
                "169.254.0.0/16", # Link-local
                "224.0.0.0/4",    # Multicast
                "240.0.0.0/4"     # Reserved
            ]
            
        if self.blocked_ports is None:
            self.blocked_ports = [
                22,    # SSH
                23,    # Telnet
                135,   # RPC
                139,   # NetBIOS
                445,   # SMB
                1433,  # SQL Server
                1521,  # Oracle
                3389,  # RDP
                5432,  # PostgreSQL
                5984,  # CouchDB
                6379,  # Redis
                8086,  # InfluxDB
                9200,  # Elasticsearch
                27017  # MongoDB
            ]


class NetworkValidator:
    """
    Network validation and security enforcement for security tool sandbox
    """
    
    def __init__(self, policy: NetworkPolicy = None):
        """
        Initialize network validator with security policy
        
        Args:
            policy: Network access policy (uses default if None)
        """
        self.policy = policy or NetworkPolicy()
        self.logger = logger
        
    def validate_target(self, target: str) -> Tuple[bool, str]:
        """
        Validate a single target against network policy
        
        Args:
            target: Target IP address, hostname, or CIDR range
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Normalize target
            target = target.strip().lower()
            
            # Check for obviously malicious patterns
            if self._contains_malicious_patterns(target):
                return False, "Target contains potentially malicious patterns"
            
            # Handle CIDR ranges
            if '/' in target:
                return self._validate_cidr_range(target)
            
            # Handle hostnames vs IP addresses
            if self._is_ip_address(target):
                return self._validate_ip_address(target)
            else:
                return self._validate_hostname(target)
                
        except Exception as e:
            self.logger.error(f"Error validating target {target}: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def validate_targets(self, targets: List[str]) -> Dict[str, Any]:
        """
        Validate multiple targets against network policy
        
        Args:
            targets: List of target IP addresses, hostnames, or CIDR ranges
            
        Returns:
            Dictionary with validation results
        """
        if len(targets) > self.policy.max_targets:
            return {
                'valid': False,
                'reason': f"Too many targets: {len(targets)} > {self.policy.max_targets}",
                'valid_targets': [],
                'invalid_targets': targets
            }
        
        valid_targets = []
        invalid_targets = []
        reasons = []
        
        for target in targets:
            is_valid, reason = self.validate_target(target)
            if is_valid:
                valid_targets.append(target)
            else:
                invalid_targets.append(target)
                reasons.append(f"{target}: {reason}")
        
        return {
            'valid': len(invalid_targets) == 0,
            'valid_targets': valid_targets,
            'invalid_targets': invalid_targets,
            'reasons': reasons,
            'total_targets': len(targets),
            'valid_count': len(valid_targets),
            'invalid_count': len(invalid_targets)
        }
    
    def validate_port_range(self, port_range: str) -> Tuple[bool, str]:
        """
        Validate port range against policy
        
        Args:
            port_range: Port range specification (e.g., "80", "80-443", "1-1000")
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            if '-' in port_range:
                start_port, end_port = port_range.split('-', 1)
                start_port = int(start_port.strip())
                end_port = int(end_port.strip())
                
                if start_port > end_port:
                    return False, "Invalid port range: start > end"
                
                if end_port - start_port > 10000:
                    return False, "Port range too large (>10000 ports)"
                
                ports_to_check = range(start_port, end_port + 1)
            else:
                ports_to_check = [int(port_range.strip())]
            
            # Check against blocked ports
            blocked_ports_in_range = [p for p in ports_to_check if p in self.policy.blocked_ports]
            if blocked_ports_in_range:
                return False, f"Range includes blocked ports: {blocked_ports_in_range}"
            
            # Check allowed ports if specified
            if self.policy.allowed_ports:
                disallowed_ports = [p for p in ports_to_check if p not in self.policy.allowed_ports]
                if disallowed_ports:
                    return False, f"Range includes disallowed ports: {disallowed_ports}"
            
            return True, "Port range valid"
            
        except ValueError:
            return False, "Invalid port range format"
        except Exception as e:
            return False, f"Port validation error: {str(e)}"
    
    def _contains_malicious_patterns(self, target: str) -> bool:
        """Check for obviously malicious patterns in target"""
        malicious_patterns = [
            r'[;&|`$()]',           # Command injection
            r'\.\./',               # Directory traversal  
            r'<script',             # XSS attempts
            r'javascript:',         # JavaScript URLs
            r'file://',             # Local file URLs
            r'ftp://',              # FTP URLs
            r'[<>"\']',             # HTML/SQL injection chars
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, target, re.IGNORECASE):
                return True
        
        return False
    
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is an IP address"""
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False
    
    def _validate_ip_address(self, ip: str) -> Tuple[bool, str]:
        """Validate IP address against policy"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if it's a private IP
            if ip_obj.is_private:
                # Check against allowed private ranges
                for allowed_range in self.policy.allowed_private_ranges:
                    if ip_obj in ipaddress.ip_network(allowed_range):
                        return True, "Valid private IP"
                return False, "Private IP not in allowed ranges"
            
            # Check against blocked public ranges
            for blocked_range in self.policy.blocked_public_ranges:
                if ip_obj in ipaddress.ip_network(blocked_range):
                    return False, f"IP in blocked range: {blocked_range}"
            
            # Public IPs are generally not allowed in sandbox
            return False, "Public IP addresses not allowed in sandbox"
            
        except ValueError:
            return False, "Invalid IP address format"
    
    def _validate_hostname(self, hostname: str) -> Tuple[bool, str]:
        """Validate hostname against policy"""
        # Basic hostname format validation
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', hostname):
            return False, "Invalid hostname format"
        
        if not self.policy.dns_allowed:
            return False, "DNS resolution not allowed in policy"
        
        # Try to resolve hostname to validate and check resolved IPs
        try:
            resolved_ips = socket.getaddrinfo(hostname, None)
            for ip_info in resolved_ips:
                ip = ip_info[4][0]
                is_valid, reason = self._validate_ip_address(ip)
                if not is_valid:
                    return False, f"Hostname resolves to invalid IP {ip}: {reason}"
            
            return True, "Valid hostname with allowed IP resolutions"
            
        except socket.gaierror:
            return False, "Hostname resolution failed"
        except Exception as e:
            return False, f"Hostname validation error: {str(e)}"
    
    def _validate_cidr_range(self, cidr: str) -> Tuple[bool, str]:
        """Validate CIDR range against policy"""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            
            # Check network size limits
            if network.num_addresses > 65536:  # More than /16
                return False, "CIDR range too large (>65536 addresses)"
            
            # Check if network overlaps with allowed ranges
            if network.is_private:
                for allowed_range in self.policy.allowed_private_ranges:
                    allowed_net = ipaddress.ip_network(allowed_range)
                    if network.subnet_of(allowed_net) or network == allowed_net:
                        return True, "Valid CIDR range in allowed private space"
                return False, "CIDR range not in allowed private ranges"
            
            # Public CIDR ranges not allowed
            return False, "Public CIDR ranges not allowed in sandbox"
            
        except ValueError:
            return False, "Invalid CIDR range format"


def main():
    """CLI interface for network validation"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='MMCODE Network Validator')
    parser.add_argument('targets', nargs='+', help='Target IPs, hostnames, or CIDR ranges to validate')
    parser.add_argument('--ports', help='Port range to validate (e.g., 80-443)')
    parser.add_argument('--allow-public', action='store_true', help='Allow public IP addresses')
    parser.add_argument('--max-targets', type=int, default=1000, help='Maximum number of targets')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create policy
    policy = NetworkPolicy(max_targets=args.max_targets)
    if args.allow_public:
        policy.blocked_public_ranges = []
    
    validator = NetworkValidator(policy)
    
    # Validate targets
    result = validator.validate_targets(args.targets)
    
    # Validate ports if specified
    port_result = None
    if args.ports:
        port_result = validator.validate_port_range(args.ports)
    
    # Output results
    if args.verbose:
        print(f"Validation Results:")
        print(f"  Total targets: {result['total_targets']}")
        print(f"  Valid targets: {result['valid_count']}")
        print(f"  Invalid targets: {result['invalid_count']}")
        
        if result['invalid_targets']:
            print("\nInvalid targets:")
            for reason in result['reasons']:
                print(f"  - {reason}")
        
        if port_result:
            print(f"\nPort range validation: {'PASS' if port_result[0] else 'FAIL'}")
            if not port_result[0]:
                print(f"  Reason: {port_result[1]}")
    
    # Exit with appropriate code
    if result['valid'] and (port_result is None or port_result[0]):
        print("VALIDATION_PASSED")
        sys.exit(0)
    else:
        print("VALIDATION_FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()