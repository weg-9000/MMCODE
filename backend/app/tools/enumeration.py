"""
Enumeration and Discovery Tools
===============================

Integration for enumeration and discovery tools:
- Gobuster: Directory and DNS enumeration
- Amass: DNS enumeration and subdomain discovery
"""

import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base import BaseSecurityTool, ToolError


class GobusterTool(BaseSecurityTool):
    """Gobuster integration for directory and DNS enumeration"""
    
    @property
    def tool_name(self) -> str:
        return "gobuster"
    
    def get_default_path(self) -> str:
        return "gobuster"  # Assume in PATH
    
    def build_command(self, 
                     target: str, 
                     options: Dict[str, Any] = None) -> List[str]:
        """Build gobuster command"""
        options = options or {}
        target = self.sanitize_target(target)
        
        command = [self.tool_path]
        
        # Mode selection
        mode = options.get('mode', 'dir')  # dir, dns, vhost, fuzz
        command.append(mode)
        
        # Target URL/domain
        if mode == 'dir':
            command.extend(['-u', target])
        elif mode == 'dns':
            command.extend(['-d', target])
        elif mode == 'vhost':
            command.extend(['-u', target])
        
        # Wordlist (required)
        wordlist = options.get('wordlist')
        if wordlist:
            command.extend(['-w', wordlist])
        else:
            # Use default wordlists based on mode
            if mode == 'dir':
                command.extend(['-w', '/usr/share/wordlists/dirb/common.txt'])
            elif mode == 'dns':
                command.extend(['-w', '/usr/share/wordlists/amass/subdomains-top1mil-5000.txt'])
        
        # Output file
        output_file = str(self.output_dir / self.get_output_filename(target, 'txt'))
        command.extend(['-o', output_file])
        
        # Threads
        threads = options.get('threads', '10')
        command.extend(['-t', str(threads)])
        
        # Timeout
        timeout = options.get('timeout', '10s')
        command.extend(['--timeout', timeout])
        
        # Mode-specific options
        if mode == 'dir':
            self._add_dir_options(command, options)
        elif mode == 'dns':
            self._add_dns_options(command, options)
        elif mode == 'vhost':
            self._add_vhost_options(command, options)
        
        # Additional options
        if options.get('verbose'):
            command.append('-v')
        
        if options.get('quiet'):
            command.append('-q')
        
        # Status codes to include
        status_codes = options.get('status_codes')
        if status_codes:
            command.extend(['-s', status_codes])
        
        # Status codes to exclude
        exclude_status = options.get('exclude_status')
        if exclude_status:
            command.extend(['-b', exclude_status])
        
        # User agent
        if options.get('user_agent'):
            command.extend(['-a', options['user_agent']])
        
        # Cookies
        if options.get('cookies'):
            command.extend(['-c', options['cookies']])
        
        # Headers
        if options.get('headers'):
            for header in options['headers']:
                command.extend(['-H', header])
        
        # Proxy
        if options.get('proxy'):
            command.extend(['-p', options['proxy']])
        
        # Follow redirects
        if options.get('follow_redirects'):
            command.append('-r')
        
        # No TLS verification
        if options.get('no_tls_validation'):
            command.append('-k')
        
        return command
    
    def _add_dir_options(self, command: List[str], options: Dict[str, Any]):
        """Add directory enumeration specific options"""
        # Extensions
        extensions = options.get('extensions')
        if extensions:
            command.extend(['-x', extensions])
        
        # Exclude length
        exclude_length = options.get('exclude_length')
        if exclude_length:
            command.extend(['-n', str(exclude_length)])
        
        # Include length
        include_length = options.get('include_length')
        if include_length:
            command.extend(['-l', str(include_length)])
        
        # Wildcard detection
        if options.get('wildcard'):
            command.append('--wildcard')
    
    def _add_dns_options(self, command: List[str], options: Dict[str, Any]):
        """Add DNS enumeration specific options"""
        # Show IPs
        if options.get('show_ips', True):
            command.append('-i')
        
        # Show CNAMEs
        if options.get('show_cnames'):
            command.append('-c')
    
    def _add_vhost_options(self, command: List[str], options: Dict[str, Any]):
        """Add virtual host enumeration specific options"""
        # Domain for vhost enumeration
        domain = options.get('domain')
        if domain:
            command.extend(['--domain', domain])
    
    def parse_output(self, 
                    stdout: str, 
                    stderr: str, 
                    output_files: List[str] = None) -> List[Dict[str, Any]]:
        """Parse gobuster output"""
        findings = []
        
        # Try to parse output file first
        txt_files = [f for f in (output_files or []) if f.endswith('.txt')]
        if txt_files:
            findings.extend(self._parse_gobuster_file(txt_files[0]))
        
        # Fallback to stdout
        if not findings:
            findings.extend(self._parse_gobuster_text(stdout))
        
        return findings
    
    def _parse_gobuster_file(self, output_file: str) -> List[Dict[str, Any]]:
        """Parse gobuster output file"""
        findings = []
        
        try:
            with open(output_file, 'r') as f:
                content = f.read()
            
            findings.extend(self._parse_gobuster_text(content))
            
        except Exception as e:
            self.logger.warning(f"Failed to parse gobuster output file: {e}")
        
        return findings
    
    def _parse_gobuster_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse gobuster text output"""
        findings = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('['):
                continue
            
            # Directory enumeration format: /path (Status: 200) [Size: 1234]
            dir_match = re.match(r'(/\S+)\s+\(Status:\s+(\d+)\)\s+\[Size:\s+(\d+)\]', line)
            if dir_match:
                path, status, size = dir_match.groups()
                
                finding = {
                    'type': 'directory',
                    'path': path,
                    'status_code': int(status),
                    'size': int(size),
                    'category': 'web_enumeration',
                    'tool': 'gobuster'
                }
                
                findings.append(finding)
                continue
            
            # DNS enumeration format: subdomain.domain.com
            if '.' in line and not line.startswith('/'):
                # Simple subdomain detection
                if re.match(r'^[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,}$', line):
                    finding = {
                        'type': 'subdomain',
                        'subdomain': line,
                        'category': 'dns_enumeration',
                        'tool': 'gobuster'
                    }
                    
                    findings.append(finding)
                continue
            
            # Generic line parsing
            if line and not any(skip in line.lower() for skip in ['scanning', 'found', 'progress']):
                finding = {
                    'type': 'enumeration_result',
                    'result': line,
                    'category': 'enumeration',
                    'tool': 'gobuster'
                }
                
                findings.append(finding)
        
        return findings


class AmassToolc(BaseSecurityTool):
    """Amass integration for DNS enumeration and subdomain discovery"""
    
    @property
    def tool_name(self) -> str:
        return "amass"
    
    def get_default_path(self) -> str:
        return "amass"  # Assume in PATH
    
    def build_command(self, 
                     target: str, 
                     options: Dict[str, Any] = None) -> List[str]:
        """Build amass command"""
        options = options or {}
        target = self.sanitize_target(target)
        
        command = [self.tool_path]
        
        # Subcommand
        subcommand = options.get('subcommand', 'enum')  # enum, intel, viz, track, db
        command.append(subcommand)
        
        # Domain
        if subcommand in ['enum', 'intel']:
            command.extend(['-d', target])
        
        # Output formats
        output_base = self.get_output_filename(target, '')
        
        # JSON output
        if options.get('json_output', True):
            json_file = str(self.output_dir / f"{output_base}.json")
            command.extend(['-json', json_file])
        
        # Text output
        txt_file = str(self.output_dir / f"{output_base}.txt")
        command.extend(['-o', txt_file])
        
        # Subcommand-specific options
        if subcommand == 'enum':
            self._add_enum_options(command, options)
        elif subcommand == 'intel':
            self._add_intel_options(command, options)
        
        # Data sources
        if options.get('active'):
            command.append('-active')
        
        if options.get('passive'):
            command.append('-passive')
        
        # Brute force
        if options.get('brute'):
            command.append('-brute')
        
        # Wordlist for brute force
        wordlist = options.get('wordlist')
        if wordlist:
            command.extend(['-w', wordlist])
        
        # Configuration file
        config = options.get('config')
        if config:
            command.extend(['-config', config])
        
        # Data sources to include
        include_sources = options.get('include_sources')
        if include_sources:
            command.extend(['-src'])
        
        # Data sources to exclude
        exclude_sources = options.get('exclude_sources')
        if exclude_sources:
            for source in exclude_sources:
                command.extend(['-exclude', source])
        
        # Timeout
        timeout = options.get('timeout', '30')
        command.extend(['-timeout', str(timeout)])
        
        # Maximum DNS queries per minute
        if options.get('max_dns_queries'):
            command.extend(['-freq', str(options['max_dns_queries'])])
        
        # Verbose output
        if options.get('verbose'):
            command.append('-v')
        
        return command
    
    def _add_enum_options(self, command: List[str], options: Dict[str, Any]):
        """Add enumeration specific options"""
        # IP addresses
        if options.get('ip_addresses'):
            command.append('-ip')
        
        # Include private IPs
        if options.get('include_private'):
            command.append('-include-unresolvable')
        
        # Maximum depth
        max_depth = options.get('max_depth')
        if max_depth:
            command.extend(['-max-depth', str(max_depth)])
        
        # Minimum word length for brute force
        min_for_recursive = options.get('min_for_recursive')
        if min_for_recursive:
            command.extend(['-min-for-recursive', str(min_for_recursive)])
    
    def _add_intel_options(self, command: List[str], options: Dict[str, Any]):
        """Add intelligence gathering specific options"""
        # ASN lookup
        if options.get('asn'):
            command.append('-asn')
        
        # CIDR lookup
        if options.get('cidr'):
            command.append('-cidr')
        
        # Organization lookup
        if options.get('org'):
            command.append('-org')
        
        # WhoisIoTool lookup
        if options.get('whois'):
            command.append('-whois')
    
    def parse_output(self, 
                    stdout: str, 
                    stderr: str, 
                    output_files: List[str] = None) -> List[Dict[str, Any]]:
        """Parse amass output"""
        findings = []
        
        # Try JSON output first
        json_files = [f for f in (output_files or []) if f.endswith('.json')]
        if json_files:
            findings.extend(self._parse_amass_json(json_files[0]))
        
        # Fallback to text output
        txt_files = [f for f in (output_files or []) if f.endswith('.txt')]
        if txt_files and not findings:
            findings.extend(self._parse_amass_text(txt_files[0]))
        
        # Fallback to stdout
        if not findings:
            findings.extend(self._parse_amass_text_content(stdout))
        
        return findings
    
    def _parse_amass_json(self, json_file: str) -> List[Dict[str, Any]]:
        """Parse amass JSON output"""
        findings = []
        
        try:
            with open(json_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        result = json.loads(line)
                        finding = self._convert_amass_result(result)
                        if finding:
                            findings.append(finding)
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            self.logger.warning(f"Failed to parse amass JSON: {e}")
        
        return findings
    
    def _parse_amass_text(self, txt_file: str) -> List[Dict[str, Any]]:
        """Parse amass text output file"""
        findings = []
        
        try:
            with open(txt_file, 'r') as f:
                content = f.read()
            
            findings.extend(self._parse_amass_text_content(content))
            
        except Exception as e:
            self.logger.warning(f"Failed to parse amass text file: {e}")
        
        return findings
    
    def _parse_amass_text_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse amass text content"""
        findings = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Format: subdomain.domain.com [IP1,IP2]
            match = re.match(r'^([a-zA-Z0-9\.\-]+)\s*(?:\[([^\]]+)\])?', line)
            if match:
                subdomain = match.group(1)
                ips = match.group(2)
                
                finding = {
                    'type': 'subdomain',
                    'subdomain': subdomain,
                    'category': 'dns_enumeration',
                    'tool': 'amass'
                }
                
                if ips:
                    finding['ip_addresses'] = [ip.strip() for ip in ips.split(',')]
                
                findings.append(finding)
        
        return findings
    
    def _convert_amass_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert amass JSON result to standard finding format"""
        name = result.get('name', '')
        if not name:
            return None
        
        finding = {
            'type': 'subdomain',
            'subdomain': name,
            'category': 'dns_enumeration',
            'tool': 'amass',
            'domain': result.get('domain', ''),
            'sources': result.get('sources', []),
            'tag': result.get('tag', '')
        }
        
        # IP addresses
        addresses = result.get('addresses', [])
        if addresses:
            ips = [addr.get('ip') for addr in addresses if addr.get('ip')]
            if ips:
                finding['ip_addresses'] = ips
        
        return finding