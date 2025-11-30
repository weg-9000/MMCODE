"""
Network Security Tools
======================

Integration for network scanning and discovery tools:
- Nmap: Network mapping and port scanning with scope validation
- Masscan: High-speed port scanner
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base import BaseSecurityTool, ToolError
from ..security.scope_enforcer import ScopeEnforcementEngine
from ..security.models import SecurityAction, generate_action_id, PentestPhase


class NmapTool(BaseSecurityTool):
    """
    Nmap integration for network scanning and service detection
    
    Features:
    - Scope-validated scanning
    - Comprehensive service detection
    - Script engine support
    - Docker sandbox integration ready
    """
    
    def __init__(self, 
                 scope_enforcer: ScopeEnforcementEngine = None,
                 tool_path: str = None,
                 timeout: int = 1800,
                 output_dir: str = "/tmp/nmap_scans"):
        """
        Args:
            scope_enforcer: Scope validation engine
            tool_path: Path to nmap binary
            timeout: Execution timeout in seconds
            output_dir: Output directory for scan files
        """
        self.scope_enforcer = scope_enforcer
        super().__init__(tool_path, timeout, output_dir)
    
    @property
    def tool_name(self) -> str:
        return "nmap"
    
    def get_default_path(self) -> str:
        import shutil
        return shutil.which("nmap") or "nmap"
    
    async def scan_with_validation(self, 
                                  targets: List[str], 
                                  scan_type: str = "default",
                                  ports: str = None) -> 'ToolResult':
        """
        Execute nmap scan with scope validation
        
        Args:
            targets: List of targets to scan
            scan_type: Type of scan to perform
            ports: Port specification
            
        Returns:
            ToolResult with scan findings
        """
        if self.scope_enforcer:
            await self._validate_targets(targets)
        
        options = {
            'scan_type': scan_type,
            'ports': ports,
            'xml_output': True
        }
        
        # Single target or multi-target
        if len(targets) == 1:
            return await self.execute(targets[0], options)
        else:
            target_list = " ".join(targets)
            return await self.execute(target_list, options)
    
    async def _validate_targets(self, targets: List[str]):
        """Validate all targets against engagement scope"""
        for target in targets:
            action = SecurityAction(
                action_id=generate_action_id(),
                action_type="port_scan",
                target=target,
                tool_name="nmap",
                method="port_scan",
                phase=PentestPhase.SCANNING,
                requires_network=True
            )
            
            validation_result = await self.scope_enforcer.validate_action(action)
            
            if not validation_result.valid:
                raise ToolError(
                    f"Target {target} failed scope validation: "
                    f"{'; '.join(validation_result.all_violations)}"
                )
    
    def build_command(self, 
                     target: str, 
                     options: Dict[str, Any] = None) -> List[str]:
        """Build nmap command"""
        options = options or {}
        target = self.sanitize_target(target)
        
        command = [self.tool_path]
        
        # Scan type
        scan_type = options.get('scan_type', 'syn')
        if scan_type == 'syn':
            command.append('-sS')
        elif scan_type == 'connect':
            command.append('-sT')
        elif scan_type == 'udp':
            command.append('-sU')
        elif scan_type == 'version':
            command.extend(['-sV'])
        elif scan_type == 'os':
            command.extend(['-O'])
        elif scan_type == 'aggressive':
            command.extend(['-A'])
        
        # Port specification
        ports = options.get('ports')
        if ports:
            command.extend(['-p', str(ports)])
        elif options.get('top_ports'):
            command.extend(['--top-ports', str(options['top_ports'])])
        
        # Timing template
        timing = options.get('timing', '3')
        command.extend(['-T', str(timing)])
        
        # Script scanning
        if options.get('scripts'):
            if options['scripts'] == 'default':
                command.append('-sC')
            elif options['scripts'] == 'all':
                command.append('--script=all')
            elif options['scripts'] == 'vuln':
                command.append('--script=vuln')
            else:
                command.extend(['--script', options['scripts']])
        
        # Output formats
        output_base = self.get_output_filename(target, '')
        if options.get('xml_output', True):
            xml_file = str(self.output_dir / f"{output_base}.xml")
            command.extend(['-oX', xml_file])
        
        if options.get('normal_output'):
            normal_file = str(self.output_dir / f"{output_base}.txt")
            command.extend(['-oN', normal_file])
        
        if options.get('grepable_output'):
            grep_file = str(self.output_dir / f"{output_base}.gnmap")
            command.extend(['-oG', grep_file])
        
        # Host discovery options
        if options.get('no_ping'):
            command.append('-Pn')
        
        if options.get('ping_only'):
            command.append('-sn')
        
        # Stealth and performance options
        if options.get('fragment'):
            command.append('-f')
        
        if options.get('decoy'):
            command.extend(['-D', options['decoy']])
        
        if options.get('source_ip'):
            command.extend(['-S', options['source_ip']])
        
        if options.get('max_rate'):
            command.extend(['--max-rate', str(options['max_rate'])])
        
        if options.get('min_rate'):
            command.extend(['--min-rate', str(options['min_rate'])])
        
        # Version intensity
        if options.get('version_intensity'):
            command.extend(['--version-intensity', str(options['version_intensity'])])
        
        # Add target
        command.append(target)
        
        return command
    
    def parse_output(self, 
                    stdout: str, 
                    stderr: str, 
                    output_files: List[str] = None) -> List[Dict[str, Any]]:
        """Parse nmap output into structured findings"""
        findings = []
        
        # Try to parse XML output first (most detailed)
        xml_files = [f for f in (output_files or []) if f.endswith('.xml')]
        if xml_files:
            findings.extend(self._parse_xml_output(xml_files[0]))
        
        # Fallback to stdout parsing
        if not findings:
            findings.extend(self._parse_text_output(stdout))
        
        return findings
    
    def _parse_xml_output(self, xml_file: str) -> List[Dict[str, Any]]:
        """Parse nmap XML output"""
        findings = []
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for host in root.findall('host'):
                # Get host information
                host_info = self._extract_host_info(host)
                
                # Get port information
                ports_elem = host.find('ports')
                if ports_elem is not None:
                    for port in ports_elem.findall('port'):
                        port_info = self._extract_port_info(port, host_info)
                        if port_info:
                            findings.append(port_info)
                
                # Get OS information
                os_info = self._extract_os_info(host, host_info)
                if os_info:
                    findings.append(os_info)
                
                # Get script results
                script_findings = self._extract_script_results(host, host_info)
                findings.extend(script_findings)
        
        except Exception as e:
            self.logger.warning(f"Failed to parse nmap XML: {e}")
        
        return findings
    
    def _extract_host_info(self, host_elem) -> Dict[str, Any]:
        """Extract host information from XML"""
        host_info = {}
        
        # Get IP address
        for address in host_elem.findall('address'):
            addr_type = address.get('addrtype', 'ipv4')
            if addr_type == 'ipv4':
                host_info['ip'] = address.get('addr')
            elif addr_type == 'mac':
                host_info['mac'] = address.get('addr')
                vendor = address.get('vendor')
                if vendor:
                    host_info['mac_vendor'] = vendor
        
        # Get hostname
        hostnames = host_elem.find('hostnames')
        if hostnames is not None:
            for hostname in hostnames.findall('hostname'):
                if hostname.get('type') == 'PTR':
                    host_info['hostname'] = hostname.get('name')
                    break
        
        # Get host state
        status = host_elem.find('status')
        if status is not None:
            host_info['state'] = status.get('state')
            host_info['reason'] = status.get('reason')
        
        return host_info
    
    def _extract_port_info(self, port_elem, host_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract port information from XML"""
        port_id = port_elem.get('portid')
        protocol = port_elem.get('protocol')
        
        state_elem = port_elem.find('state')
        if state_elem is None:
            return None
        
        port_state = state_elem.get('state')
        
        # Only include open/filtered ports
        if port_state not in ['open', 'filtered']:
            return None
        
        finding = {
            'type': 'service',
            'host': host_info.get('ip'),
            'hostname': host_info.get('hostname'),
            'port': int(port_id),
            'protocol': protocol,
            'state': port_state,
            'reason': state_elem.get('reason'),
            'category': 'network_service'
        }
        
        # Get service information
        service_elem = port_elem.find('service')
        if service_elem is not None:
            finding.update({
                'service': service_elem.get('name'),
                'product': service_elem.get('product'),
                'version': service_elem.get('version'),
                'extrainfo': service_elem.get('extrainfo'),
                'tunnel': service_elem.get('tunnel'),
                'method': service_elem.get('method'),
                'confidence': service_elem.get('conf')
            })
        
        return finding
    
    def _extract_os_info(self, host_elem, host_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract OS information from XML"""
        os_elem = host_elem.find('os')
        if os_elem is None:
            return None
        
        # Get best OS match
        osmatch = os_elem.find('osmatch')
        if osmatch is None:
            return None
        
        accuracy = osmatch.get('accuracy', '0')
        if int(accuracy) < 50:  # Low confidence
            return None
        
        return {
            'type': 'os_detection',
            'host': host_info.get('ip'),
            'hostname': host_info.get('hostname'),
            'os_name': osmatch.get('name'),
            'os_accuracy': accuracy,
            'category': 'host_information'
        }
    
    def _extract_script_results(self, host_elem, host_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract script scan results from XML"""
        findings = []
        
        # Host-level scripts
        hostscript = host_elem.find('hostscript')
        if hostscript is not None:
            for script in hostscript.findall('script'):
                script_finding = self._parse_script_result(script, host_info)
                if script_finding:
                    findings.append(script_finding)
        
        # Port-level scripts
        ports_elem = host_elem.find('ports')
        if ports_elem is not None:
            for port in ports_elem.findall('port'):
                port_id = port.get('portid')
                protocol = port.get('protocol')
                
                for script in port.findall('script'):
                    script_finding = self._parse_script_result(
                        script, host_info, port_id, protocol
                    )
                    if script_finding:
                        findings.append(script_finding)
        
        return findings
    
    def _parse_script_result(self, 
                           script_elem, 
                           host_info: Dict[str, Any],
                           port: str = None,
                           protocol: str = None) -> Optional[Dict[str, Any]]:
        """Parse individual script result"""
        script_id = script_elem.get('id')
        script_output = script_elem.get('output', '')
        
        if not script_output.strip():
            return None
        
        finding = {
            'type': 'script_result',
            'host': host_info.get('ip'),
            'hostname': host_info.get('hostname'),
            'script_id': script_id,
            'script_output': script_output,
            'category': 'script_scan'
        }
        
        if port:
            finding['port'] = int(port)
            finding['protocol'] = protocol
        
        # Classify script results
        if any(vuln_keyword in script_id.lower() for vuln_keyword in ['vuln', 'exploit', 'cve']):
            finding['category'] = 'vulnerability'
        
        return finding
    
    def _parse_text_output(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse nmap text output as fallback"""
        findings = []
        
        # Basic regex patterns for parsing text output
        host_pattern = r'Nmap scan report for (.+)'
        port_pattern = r'(\d+)/(\w+)\s+(\w+)\s+(.+)'
        
        current_host = None
        
        for line in stdout.split('\n'):
            line = line.strip()
            
            # Host detection
            host_match = re.match(host_pattern, line)
            if host_match:
                current_host = host_match.group(1)
                continue
            
            # Port detection
            if current_host:
                port_match = re.match(port_pattern, line)
                if port_match:
                    port, protocol, state, service = port_match.groups()
                    
                    if state in ['open', 'filtered']:
                        findings.append({
                            'type': 'service',
                            'host': current_host,
                            'port': int(port),
                            'protocol': protocol,
                            'state': state,
                            'service': service.split()[0] if service else 'unknown',
                            'category': 'network_service'
                        })
        
        return findings
    
    def _is_partial_success(self, exit_code: int, stdout: str, stderr: str) -> bool:
        """Nmap can have partial success with non-zero exit codes"""
        # Nmap exit codes:
        # 0: Success
        # 1: Error
        # 2: Fatal error
        return exit_code == 1 and "scan report" in stdout.lower()


class MasscanTool(BaseSecurityTool):
    """Masscan integration for high-speed port scanning"""
    
    @property
    def tool_name(self) -> str:
        return "masscan"
    
    def get_default_path(self) -> str:
        return "masscan"  # Assume in PATH
    
    def build_command(self, 
                     target: str, 
                     options: Dict[str, Any] = None) -> List[str]:
        """Build masscan command"""
        options = options or {}
        target = self.sanitize_target(target)
        
        command = [self.tool_path]
        
        # Port specification (required)
        ports = options.get('ports', '1-65535')
        command.extend(['-p', str(ports)])
        
        # Rate limiting
        rate = options.get('rate', '1000')
        command.extend(['--rate', str(rate)])
        
        # Output format
        output_file = str(self.output_dir / self.get_output_filename(target, 'xml'))
        command.extend(['-oX', output_file])
        
        # Additional options
        if options.get('banners'):
            command.append('--banners')
        
        if options.get('source_ip'):
            command.extend(['--source-ip', options['source_ip']])
        
        if options.get('interface'):
            command.extend(['-e', options['interface']])
        
        # Add target
        command.append(target)
        
        return command
    
    def parse_output(self, 
                    stdout: str, 
                    stderr: str, 
                    output_files: List[str] = None) -> List[Dict[str, Any]]:
        """Parse masscan output"""
        findings = []
        
        # Parse XML output
        xml_files = [f for f in (output_files or []) if f.endswith('.xml')]
        if xml_files:
            findings.extend(self._parse_masscan_xml(xml_files[0]))
        
        return findings
    
    def _parse_masscan_xml(self, xml_file: str) -> List[Dict[str, Any]]:
        """Parse masscan XML output"""
        findings = []
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for host in root.findall('host'):
                # Get host address
                address_elem = host.find('address')
                if address_elem is None:
                    continue
                
                host_ip = address_elem.get('addr')
                
                # Get ports
                ports_elem = host.find('ports')
                if ports_elem is not None:
                    for port in ports_elem.findall('port'):
                        port_id = port.get('portid')
                        protocol = port.get('protocol')
                        
                        state_elem = port.find('state')
                        if state_elem is not None:
                            state = state_elem.get('state')
                            
                            finding = {
                                'type': 'service',
                                'host': host_ip,
                                'port': int(port_id),
                                'protocol': protocol,
                                'state': state,
                                'category': 'network_service',
                                'tool': 'masscan'
                            }
                            
                            # Get service info if available
                            service_elem = port.find('service')
                            if service_elem is not None:
                                finding['service'] = service_elem.get('name')
                                finding['banner'] = service_elem.get('banner')
                            
                            findings.append(finding)
        
        except Exception as e:
            self.logger.warning(f"Failed to parse masscan XML: {e}")
        
        return findings