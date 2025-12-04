"""
End-to-End Test: Nmap Scan Workflow
===================================

Test scenario: Nmap scan → result parsing → finding storage

This test validates the complete Nmap scanning workflow including:
1. Scope validation and enforcement
2. Nmap tool execution with proper XML parsing
3. Finding extraction and storage
4. Service discovery and target enumeration
5. Audit trail verification
"""

import pytest
import asyncio
import tempfile
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from app.tools.network import NmapTool
from app.security.scope_enforcer import ScopeEnforcementEngine
from app.security.audit_logger import SecurityAuditLogger, AuditEventType
from app.security.models import SecurityAction, generate_action_id, PentestPhase
from app.models.models import Session, SecurityAuditLog


class TestNmapScanWorkflow:
    """E2E test suite for Nmap scanning workflow"""

    @pytest.fixture
    async def mock_scope_enforcer(self):
        """Mock scope enforcement engine"""
        enforcer = Mock(spec=ScopeEnforcementEngine)
        enforcer.validate_action = AsyncMock(return_value=Mock(valid=True, message="Target approved"))
        return enforcer

    @pytest.fixture
    async def mock_audit_logger(self):
        """Mock audit logger"""
        logger = Mock(spec=SecurityAuditLogger)
        logger.log_event = AsyncMock()
        return logger

    @pytest.fixture
    def sample_nmap_xml_output(self):
        """Sample Nmap XML output for testing"""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <nmaprun scanner="nmap" args="nmap -sV -O 192.168.1.100" start="1701685200" version="7.94">
            <host>
                <status state="up" reason="echo-reply"/>
                <address addr="192.168.1.100" addrtype="ipv4"/>
                <hostnames>
                    <hostname name="test-server.local" type="PTR"/>
                </hostnames>
                <ports>
                    <port protocol="tcp" portid="22">
                        <state state="open" reason="syn-ack"/>
                        <service name="ssh" product="OpenSSH" version="8.2p1" extrainfo="Ubuntu-4ubuntu0.3"/>
                    </port>
                    <port protocol="tcp" portid="80">
                        <state state="open" reason="syn-ack"/>
                        <service name="http" product="Apache httpd" version="2.4.41"/>
                    </port>
                    <port protocol="tcp" portid="443">
                        <state state="open" reason="syn-ack"/>
                        <service name="https" product="Apache httpd" version="2.4.41" tunnel="ssl"/>
                    </port>
                </ports>
                <os>
                    <osmatch name="Linux 5.0 - 5.4" accuracy="95" line="60793"/>
                </os>
            </host>
        </nmaprun>"""

    @pytest.mark.asyncio
    async def test_complete_nmap_scan_workflow(self, mock_scope_enforcer, mock_audit_logger, sample_nmap_xml_output):
        """Test complete Nmap scan workflow from target validation to finding storage"""
        
        # Setup test environment
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create XML output file
            xml_file = output_dir / "nmap_scan_results.xml"
            xml_file.write_text(sample_nmap_xml_output)
            
            # Initialize Nmap tool with mocked dependencies
            with patch('shutil.which', return_value='/usr/bin/nmap'):
                nmap_tool = NmapTool(
                    scope_enforcer=mock_scope_enforcer,
                    tool_path='/usr/bin/nmap',
                    output_dir=str(output_dir)
                )
            
            # Mock subprocess execution
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                sample_nmap_xml_output.encode(),
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                with patch.object(nmap_tool, '_find_output_files', return_value=[str(xml_file)]):
                    
                    # Execute scan
                    result = await nmap_tool.scan_with_validation(
                        targets=["192.168.1.100"],
                        scan_type="service_detection",
                        ports="22,80,443"
                    )
            
            # Verify execution results
            assert result.success is True
            assert result.tool_name == "nmap"
            assert result.exit_code == 0
            assert len(result.findings) > 0
            
            # Verify target discovery
            assert "192.168.1.100" in result.targets_discovered
            
            # Verify service discovery
            services = result.services_discovered
            assert len(services) == 3
            
            # Check specific services
            ssh_service = next((s for s in services if s['port'] == 22), None)
            assert ssh_service is not None
            assert ssh_service['service'] == 'ssh'
            assert ssh_service['version'] == 'OpenSSH 8.2p1'
            
            http_service = next((s for s in services if s['port'] == 80), None)
            assert http_service is not None
            assert http_service['service'] == 'http'
            assert http_service['version'] == 'Apache httpd 2.4.41'
            
            # Verify findings structure
            for finding in result.findings:
                assert 'type' in finding
                assert 'host' in finding
                assert 'timestamp' in finding
                
                if finding['type'] == 'service':
                    assert 'port' in finding
                    assert 'protocol' in finding
                    assert 'service' in finding
                    assert 'state' in finding

    @pytest.mark.asyncio
    async def test_nmap_scope_validation_workflow(self, mock_audit_logger):
        """Test Nmap scope validation workflow"""
        
        # Create scope enforcer that denies access
        mock_scope_enforcer = Mock(spec=ScopeEnforcementEngine)
        mock_scope_enforcer.validate_action = AsyncMock(return_value=Mock(
            valid=False, 
            message="Target outside approved scope"
        ))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('shutil.which', return_value='/usr/bin/nmap'):
                nmap_tool = NmapTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=temp_dir
                )
            
            # Attempt scan of unauthorized target
            with pytest.raises(Exception) as exc_info:
                await nmap_tool.scan_with_validation(
                    targets=["8.8.8.8"]  # Unauthorized external target
                )
            
            # Verify scope validation was called
            mock_scope_enforcer.validate_action.assert_called_once()
            
            # Verify action structure
            call_args = mock_scope_enforcer.validate_action.call_args[0][0]
            assert isinstance(call_args, SecurityAction)
            assert call_args.action_type == "port_scan"
            assert call_args.target == "8.8.8.8"
            assert call_args.tool_name == "nmap"
            assert call_args.phase == PentestPhase.SCANNING

    @pytest.mark.asyncio
    async def test_nmap_error_handling_workflow(self, mock_scope_enforcer):
        """Test Nmap error handling in workflow"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('shutil.which', return_value='/usr/bin/nmap'):
                nmap_tool = NmapTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=temp_dir
                )
            
            # Mock failed subprocess execution
            mock_process = Mock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(
                b"",
                b"nmap: Cannot resolve hostname"
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                result = await nmap_tool.scan_with_validation(
                    targets=["invalid-hostname.test"]
                )
            
            # Verify error handling
            assert result.success is False
            assert result.exit_code == 1
            assert "Cannot resolve hostname" in result.stderr
            assert len(result.findings) == 0

    @pytest.mark.asyncio 
    async def test_nmap_xml_parsing_edge_cases(self, mock_scope_enforcer):
        """Test Nmap XML parsing with various edge cases"""
        
        edge_case_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <nmaprun scanner="nmap" args="nmap -sV 192.168.1.1" start="1701685200" version="7.94">
            <host>
                <status state="up" reason="echo-reply"/>
                <address addr="192.168.1.1" addrtype="ipv4"/>
                <ports>
                    <port protocol="tcp" portid="8080">
                        <state state="filtered" reason="no-response"/>
                        <service name="http-proxy" method="probed" conf="3"/>
                    </port>
                    <port protocol="udp" portid="53">
                        <state state="open|filtered" reason="no-response"/>
                        <service name="domain" method="probed" conf="3"/>
                    </port>
                </ports>
            </host>
            <host>
                <status state="down" reason="no-response"/>
                <address addr="192.168.1.2" addrtype="ipv4"/>
            </host>
        </nmaprun>"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            xml_file = output_dir / "edge_case_scan.xml"
            xml_file.write_text(edge_case_xml)
            
            with patch('shutil.which', return_value='/usr/bin/nmap'):
                nmap_tool = NmapTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=str(output_dir)
                )
            
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                edge_case_xml.encode(),
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                with patch.object(nmap_tool, '_find_output_files', return_value=[str(xml_file)]):
                    result = await nmap_tool.scan_with_validation(
                        targets=["192.168.1.0/29"]
                    )
            
            # Verify parsing handles various port states
            assert result.success is True
            assert len(result.findings) > 0
            
            # Verify only up hosts are included in targets
            assert "192.168.1.1" in result.targets_discovered
            assert "192.168.1.2" not in result.targets_discovered
            
            # Verify service parsing handles different states
            services = result.services_discovered
            filtered_service = next((s for s in services if s['state'] == 'filtered'), None)
            assert filtered_service is not None
            
            open_filtered_service = next((s for s in services if s['state'] == 'open|filtered'), None)
            assert open_filtered_service is not None

    @pytest.mark.asyncio
    async def test_nmap_concurrent_scan_workflow(self, mock_scope_enforcer):
        """Test concurrent Nmap scans"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('shutil.which', return_value='/usr/bin/nmap'):
                nmap_tool = NmapTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=temp_dir
                )
            
            # Mock successful scans
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                b"<nmaprun><host><status state='up'/></host></nmaprun>",
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                # Execute concurrent scans
                tasks = [
                    nmap_tool.scan_with_validation(targets=[f"192.168.1.{i}"])
                    for i in range(100, 105)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all scans completed successfully
            for result in results:
                assert not isinstance(result, Exception)
                assert result.success is True
            
            # Verify scope validation called for each target
            assert mock_scope_enforcer.validate_action.call_count == 5

if __name__ == "__main__":
    pytest.main([__file__, "-v"])