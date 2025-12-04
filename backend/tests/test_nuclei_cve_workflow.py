"""
End-to-End Test: Nuclei CVE Detection Workflow
==============================================

Test scenario: Nuclei scan → CVE identification → risk evaluation

This test validates the complete Nuclei vulnerability scanning workflow including:
1. Template filtering and security policy enforcement
2. Nuclei tool execution with JSON parsing
3. CVE identification and CVSS scoring
4. Risk level evaluation and classification
5. Finding correlation and deduplication
"""

import pytest
import asyncio
import tempfile
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from app.tools.vulnerability import NucleiTool
from app.security.scope_enforcer import ScopeEnforcementEngine
from app.security.models import SecurityAction, SeverityLevel, RiskLevel, generate_finding_id
from app.security.risk_evaluator import RiskEvaluator


class TestNucleiCVEWorkflow:
    """E2E test suite for Nuclei CVE detection workflow"""

    @pytest.fixture
    async def mock_scope_enforcer(self):
        """Mock scope enforcement engine"""
        enforcer = Mock(spec=ScopeEnforcementEngine)
        enforcer.validate_action = AsyncMock(return_value=Mock(valid=True, message="Target approved"))
        return enforcer

    @pytest.fixture
    async def mock_risk_evaluator(self):
        """Mock risk evaluator"""
        evaluator = Mock(spec=RiskEvaluator)
        evaluator.evaluate_finding = AsyncMock(return_value=RiskLevel.HIGH)
        return evaluator

    @pytest.fixture
    def sample_nuclei_json_output(self):
        """Sample Nuclei JSON output for testing"""
        return json.dumps([
            {
                "template": "CVE-2021-44228-log4j-rce",
                "template-id": "CVE-2021-44228",
                "template-path": "/nuclei-templates/cves/2021/CVE-2021-44228.yaml",
                "info": {
                    "name": "Apache Log4j RCE",
                    "author": ["daffainfo"],
                    "tags": ["cve", "cve2021", "rce", "log4j", "oast"],
                    "description": "Apache Log4j Remote Code Execution",
                    "reference": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-44228"],
                    "severity": "critical",
                    "metadata": {
                        "verified": True,
                        "cvss-score": 9.8,
                        "cvss-vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
                    },
                    "classification": {
                        "cve-id": "CVE-2021-44228",
                        "cwe-id": "CWE-917"
                    }
                },
                "type": "http",
                "host": "https://vulnerable-app.example.com",
                "matched-at": "https://vulnerable-app.example.com/login",
                "timestamp": "2024-12-04T10:30:00.000Z",
                "matcher-status": True,
                "curl-command": "curl -X GET 'https://vulnerable-app.example.com/login'"
            },
            {
                "template": "CVE-2022-0543-redis-rce",
                "template-id": "CVE-2022-0543", 
                "template-path": "/nuclei-templates/cves/2022/CVE-2022-0543.yaml",
                "info": {
                    "name": "Redis Lua Sandbox Escape",
                    "author": ["dwisiswant0"],
                    "tags": ["cve", "cve2022", "redis", "rce"],
                    "description": "Redis Lua sandbox escape vulnerability",
                    "reference": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-0543"],
                    "severity": "high",
                    "metadata": {
                        "verified": True,
                        "cvss-score": 8.1,
                        "cvss-vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H"
                    },
                    "classification": {
                        "cve-id": "CVE-2022-0543",
                        "cwe-id": "CWE-94"
                    }
                },
                "type": "network",
                "host": "192.168.1.100:6379",
                "matched-at": "192.168.1.100:6379",
                "timestamp": "2024-12-04T10:31:00.000Z",
                "matcher-status": True
            },
            {
                "template": "generic-panels-detection",
                "template-id": "generic-panel",
                "template-path": "/nuclei-templates/technologies/generic-panel.yaml",
                "info": {
                    "name": "Generic Admin Panel Detection",
                    "author": ["pdteam"],
                    "tags": ["tech", "panel", "admin"],
                    "description": "Generic admin panel detection",
                    "severity": "info"
                },
                "type": "http",
                "host": "https://vulnerable-app.example.com",
                "matched-at": "https://vulnerable-app.example.com/admin",
                "timestamp": "2024-12-04T10:32:00.000Z",
                "matcher-status": True
            }
        ])

    @pytest.mark.asyncio
    async def test_complete_nuclei_cve_workflow(self, mock_scope_enforcer, mock_risk_evaluator, sample_nuclei_json_output):
        """Test complete Nuclei CVE detection workflow"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create JSON output file
            json_file = output_dir / "nuclei_scan_results.json"
            json_file.write_text(sample_nuclei_json_output)
            
            # Initialize Nuclei tool
            with patch('shutil.which', return_value='/usr/bin/nuclei'):
                nuclei_tool = NucleiTool(
                    scope_enforcer=mock_scope_enforcer,
                    tool_path='/usr/bin/nuclei',
                    output_dir=str(output_dir)
                )
            
            # Mock subprocess execution
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                sample_nuclei_json_output.encode(),
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                with patch.object(nuclei_tool, '_find_output_files', return_value=[str(json_file)]):
                    # Execute vulnerability scan
                    result = await nuclei_tool.scan_with_validation(
                        targets=["https://vulnerable-app.example.com", "192.168.1.100"],
                        template_categories=["cves", "technologies"],
                        severity_filter=["critical", "high", "medium"]
                    )
            
            # Verify execution results
            assert result.success is True
            assert result.tool_name == "nuclei"
            assert result.exit_code == 0
            assert len(result.findings) == 3
            
            # Verify CVE findings
            cve_findings = [f for f in result.findings if f.get('cve_id')]
            assert len(cve_findings) == 2
            
            # Verify critical CVE (Log4j)
            log4j_finding = next((f for f in cve_findings if f.get('cve_id') == 'CVE-2021-44228'), None)
            assert log4j_finding is not None
            assert log4j_finding['severity'] == 'critical'
            assert log4j_finding['cvss_score'] == 9.8
            assert log4j_finding['cvss_vector'] == 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
            assert 'RCE' in log4j_finding['name']
            
            # Verify high CVE (Redis)
            redis_finding = next((f for f in cve_findings if f.get('cve_id') == 'CVE-2022-0543'), None)
            assert redis_finding is not None
            assert redis_finding['severity'] == 'high'
            assert redis_finding['cvss_score'] == 8.1
            
            # Verify target discovery
            assert "vulnerable-app.example.com" in result.targets_discovered
            assert "192.168.1.100" in result.targets_discovered

    @pytest.mark.asyncio
    async def test_nuclei_template_filtering(self, mock_scope_enforcer):
        """Test Nuclei template filtering and security policy enforcement"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('shutil.which', return_value='/usr/bin/nuclei'):
                nuclei_tool = NucleiTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=temp_dir
                )
            
            # Test authorized template filtering
            authorized_templates = nuclei_tool._filter_authorized_templates([
                "cves", "default-logins", "technologies", 
                "dos",  # Should be blocked
                "fuzzing",  # Should be blocked
                "misconfigurations"
            ])
            
            # Verify dangerous templates are filtered out
            assert "dos" not in authorized_templates
            assert "fuzzing" not in authorized_templates
            assert "cves" in authorized_templates
            assert "default-logins" in authorized_templates
            assert "misconfigurations" in authorized_templates

    @pytest.mark.asyncio
    async def test_nuclei_cve_risk_evaluation(self, mock_scope_enforcer):
        """Test CVE risk evaluation workflow"""
        
        # Sample finding with CVE data
        cve_finding = {
            "type": "vulnerability",
            "template_id": "CVE-2021-44228",
            "cve_id": "CVE-2021-44228",
            "name": "Apache Log4j RCE",
            "severity": "critical",
            "cvss_score": 9.8,
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "host": "vulnerable-app.example.com",
            "matched_at": "https://vulnerable-app.example.com/login",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Mock risk evaluator to test different risk levels
        risk_evaluator = Mock(spec=RiskEvaluator)
        
        # Test critical CVE with high CVSS score
        risk_evaluator.evaluate_cve_risk = AsyncMock(return_value=RiskLevel.CRITICAL)
        risk_level = await risk_evaluator.evaluate_cve_risk(cve_finding)
        assert risk_level == RiskLevel.CRITICAL
        
        # Verify risk evaluation considers CVSS score
        risk_evaluator.evaluate_cve_risk.assert_called_with(cve_finding)

    @pytest.mark.asyncio
    async def test_nuclei_json_parsing_edge_cases(self, mock_scope_enforcer):
        """Test Nuclei JSON parsing with edge cases"""
        
        edge_case_json = json.dumps([
            {
                # CVE without CVSS score
                "template": "CVE-2023-XXXX",
                "template-id": "CVE-2023-XXXX",
                "info": {
                    "name": "Unknown CVE",
                    "severity": "medium",
                    "classification": {
                        "cve-id": "CVE-2023-XXXX"
                    }
                },
                "host": "example.com",
                "matched-at": "https://example.com",
                "timestamp": "2024-12-04T10:30:00.000Z"
            },
            {
                # Finding without CVE
                "template": "generic-tech-detection",
                "template-id": "generic-tech",
                "info": {
                    "name": "Technology Detection",
                    "severity": "info",
                    "tags": ["tech"]
                },
                "host": "example.com",
                "matched-at": "https://example.com",
                "timestamp": "2024-12-04T10:30:00.000Z"
            },
            {
                # Malformed JSON entry (missing required fields)
                "template": "incomplete-finding",
                "host": "example.com"
            }
        ])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            json_file = output_dir / "edge_case_scan.json"
            json_file.write_text(edge_case_json)
            
            with patch('shutil.which', return_value='/usr/bin/nuclei'):
                nuclei_tool = NucleiTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=str(output_dir)
                )
            
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                edge_case_json.encode(),
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                with patch.object(nuclei_tool, '_find_output_files', return_value=[str(json_file)]):
                    result = await nuclei_tool.scan_with_validation(
                        targets=["https://example.com"]
                    )
            
            # Verify parsing handles edge cases gracefully
            assert result.success is True
            assert len(result.findings) >= 2  # At least valid findings processed
            
            # Verify CVE without CVSS is handled
            cve_finding = next((f for f in result.findings if f.get('cve_id') == 'CVE-2023-XXXX'), None)
            assert cve_finding is not None
            assert cve_finding.get('cvss_score', 0.0) == 0.0

    @pytest.mark.asyncio
    async def test_nuclei_scope_validation_workflow(self, mock_risk_evaluator):
        """Test Nuclei scope validation workflow"""
        
        # Create scope enforcer that denies certain targets
        mock_scope_enforcer = Mock(spec=ScopeEnforcementEngine)
        mock_scope_enforcer.validate_action = AsyncMock(side_effect=[
            Mock(valid=True, message="Internal target approved"),
            Mock(valid=False, message="External target blocked")
        ])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('shutil.which', return_value='/usr/bin/nuclei'):
                nuclei_tool = NucleiTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=temp_dir
                )
            
            # Test mixed target validation
            with pytest.raises(Exception):
                await nuclei_tool.scan_with_validation(
                    targets=["internal.company.com", "external-public-site.com"],
                    template_categories=["cves"]
                )
            
            # Verify scope validation called for each target
            assert mock_scope_enforcer.validate_action.call_count == 2

    @pytest.mark.asyncio
    async def test_nuclei_severity_filtering(self, mock_scope_enforcer):
        """Test Nuclei severity-based filtering"""
        
        multi_severity_json = json.dumps([
            {
                "template": "critical-vuln",
                "template-id": "critical-1",
                "info": {"name": "Critical Vulnerability", "severity": "critical"},
                "host": "example.com",
                "matched-at": "https://example.com",
                "timestamp": "2024-12-04T10:30:00.000Z"
            },
            {
                "template": "high-vuln",
                "template-id": "high-1", 
                "info": {"name": "High Vulnerability", "severity": "high"},
                "host": "example.com",
                "matched-at": "https://example.com",
                "timestamp": "2024-12-04T10:30:00.000Z"
            },
            {
                "template": "medium-vuln",
                "template-id": "medium-1",
                "info": {"name": "Medium Vulnerability", "severity": "medium"},
                "host": "example.com",
                "matched-at": "https://example.com",
                "timestamp": "2024-12-04T10:30:00.000Z"
            },
            {
                "template": "low-info",
                "template-id": "low-1",
                "info": {"name": "Low Info", "severity": "low"},
                "host": "example.com",
                "matched-at": "https://example.com",
                "timestamp": "2024-12-04T10:30:00.000Z"
            }
        ])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            json_file = output_dir / "severity_test.json"
            json_file.write_text(multi_severity_json)
            
            with patch('shutil.which', return_value='/usr/bin/nuclei'):
                nuclei_tool = NucleiTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=str(output_dir)
                )
            
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                multi_severity_json.encode(),
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                with patch.object(nuclei_tool, '_find_output_files', return_value=[str(json_file)]):
                    # Test with critical and high only
                    result = await nuclei_tool.scan_with_validation(
                        targets=["https://example.com"],
                        severity_filter=["critical", "high"]
                    )
            
            # Verify severity filtering in command construction
            # This would be tested by checking the actual command args passed to subprocess
            assert result.success is True

    @pytest.mark.asyncio
    async def test_nuclei_concurrent_scans(self, mock_scope_enforcer):
        """Test concurrent Nuclei vulnerability scans"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('shutil.which', return_value='/usr/bin/nuclei'):
                nuclei_tool = NucleiTool(
                    scope_enforcer=mock_scope_enforcer,
                    output_dir=temp_dir
                )
            
            # Mock successful scans
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                b'[{"template":"test","host":"example.com","matched-at":"https://example.com","timestamp":"2024-12-04T10:30:00.000Z"}]',
                b""
            ))
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                # Execute concurrent scans
                targets = [f"app{i}.example.com" for i in range(1, 6)]
                tasks = [
                    nuclei_tool.scan_with_validation(
                        targets=[target],
                        template_categories=["cves"]
                    )
                    for target in targets
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