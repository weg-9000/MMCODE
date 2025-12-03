"""
Security Tools Integration Test
===============================

Simple integration test to verify Nmap and Nuclei tools work with approval system
"""

import asyncio
import logging
from pathlib import Path

from .network import NmapTool
from .vulnerability import NucleiTool
from ..security.approval_integration import ApprovalIntegrationManager
from ..security.scope_enforcer import ScopeEnforcementEngine
from ..db.session import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_nmap_integration():
    """Test Nmap tool integration"""
    logger.info("Testing Nmap integration...")
    
    try:
        # Initialize tools
        nmap = NmapTool(
            tool_path="/usr/bin/nmap",  # Adjust path as needed
            timeout=300,
            output_dir="/tmp/mmcode_test"
        )
        
        # Test basic command building
        target = "scanme.nmap.org"
        options = {
            'scan_type': 'syn',
            'ports': '22,80,443',
            'timing': '3'
        }
        
        command = nmap.build_command(target, options)
        logger.info(f"Nmap command: {' '.join(command)}")
        
        # Test with localhost (safe target)
        localhost_result = await nmap.execute("127.0.0.1", {
            'scan_type': 'connect',
            'ports': '22,80,443',
            'timing': '3'
        })
        
        logger.info(f"Nmap result: {localhost_result.success}")
        logger.info(f"Findings count: {len(localhost_result.findings)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Nmap integration test failed: {e}")
        return False


async def test_nuclei_integration():
    """Test Nuclei tool integration"""
    logger.info("Testing Nuclei integration...")
    
    try:
        # Initialize tools
        nuclei = NucleiTool(
            tool_path="/usr/bin/nuclei",  # Adjust path as needed
            timeout=300,
            output_dir="/tmp/mmcode_test"
        )
        
        # Test basic command building
        target = "http://example.com"
        options = {
            'templates': ['cves/'],
            'severity': 'critical,high',
            'concurrency': '10'
        }
        
        command = nuclei.build_command(target, options)
        logger.info(f"Nuclei command: {' '.join(command)}")
        
        # Test template filtering
        authorized = nuclei._filter_authorized_templates(['cves', 'dos'])
        logger.info(f"Authorized templates: {authorized}")
        assert 'cves/' in authorized
        assert 'dos/' not in authorized  # Should be blocked
        
        return True
        
    except Exception as e:
        logger.error(f"Nuclei integration test failed: {e}")
        return False


async def test_approval_integration():
    """Test approval system integration with tools"""
    logger.info("Testing approval system integration...")
    
    try:
        # Mock database session
        # In real implementation, use actual database
        db_session = None
        
        approval_manager = ApprovalIntegrationManager(db_session)
        
        # Test high-risk tool detection
        from ..security.models import SecurityAction, PentestPhase, RiskLevel
        
        high_risk_action = SecurityAction(
            action_id="test-001",
            action_type="port_scan",
            target="192.168.1.1",
            tool_name="nmap",
            command="nmap -sS -p- 192.168.1.1",
            phase=PentestPhase.SCANNING,
            risk_level=RiskLevel.HIGH,
            requires_network=True
        )
        
        # This should require approval for high-risk scan
        requires_approval = await approval_manager.check_approval_required(high_risk_action)
        logger.info(f"High-risk action requires approval: {requires_approval}")
        assert requires_approval == True
        
        # Test low-risk action
        low_risk_action = SecurityAction(
            action_id="test-002",
            action_type="port_scan",
            target="127.0.0.1",
            tool_name="nmap",
            command="nmap -sT -p 80,443 127.0.0.1",
            phase=PentestPhase.SCANNING,
            risk_level=RiskLevel.LOW,
            requires_network=True
        )
        
        requires_approval = await approval_manager.check_approval_required(low_risk_action)
        logger.info(f"Low-risk action requires approval: {requires_approval}")
        # Low-risk might still require approval based on configuration
        
        return True
        
    except Exception as e:
        logger.error(f"Approval integration test failed: {e}")
        return False


async def main():
    """Run all integration tests"""
    logger.info("Starting MMCODE Security Tools Integration Tests...")
    
    tests = [
        test_nmap_integration,
        test_nuclei_integration, 
        test_approval_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} failed: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        logger.info("✅ All integration tests passed!")
    else:
        logger.warning("⚠️  Some tests failed - check configuration")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)