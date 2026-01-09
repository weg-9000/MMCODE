"""
MMCODE Security Platform - Risk Evaluator
=========================================

Risk evaluation system for security findings and operations
- CVSS-based risk scoring
- Context-aware risk assessment
- Threat intelligence integration
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime, timezone
from dataclasses import dataclass

from .models import RiskLevel, SeverityLevel

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_level: RiskLevel
    risk_score: float
    severity: SeverityLevel
    factors: List[str]
    recommendations: List[str]
    confidence: float
    assessment_time: datetime
    

class RiskEvaluator:
    """
    Comprehensive risk evaluation for security findings and operations
    """
    
    # CVSS score to risk level mapping
    CVSS_RISK_MAPPING = {
        (0.0, 3.9): RiskLevel.LOW,
        (4.0, 6.9): RiskLevel.MEDIUM, 
        (7.0, 8.9): RiskLevel.HIGH,
        (9.0, 10.0): RiskLevel.CRITICAL
    }
    
    # CVE age impact factors
    CVE_AGE_FACTORS = {
        30: 1.2,    # Recent CVEs (last 30 days) get 20% boost
        90: 1.1,    # CVEs from last 90 days get 10% boost
        365: 1.0,   # CVEs from last year - baseline
        1095: 0.9,  # CVEs older than 3 years get 10% reduction
    }
    
    def __init__(self):
        """Initialize risk evaluator"""
        self.threat_intelligence = {}
        self.context_factors = {}
        
    async def evaluate_finding(self, finding: Dict[str, Any], context: Dict[str, Any] = None) -> RiskAssessment:
        """
        Evaluate risk level for a security finding
        
        Args:
            finding: Security finding data
            context: Additional context (target info, environment, etc.)
            
        Returns:
            RiskAssessment with calculated risk level and details
        """
        context = context or {}
        
        # Extract base risk from finding
        base_risk = self._calculate_base_risk(finding)
        
        # Apply context modifiers
        context_risk = self._apply_context_modifiers(base_risk, finding, context)
        
        # Apply threat intelligence
        final_risk = await self._apply_threat_intelligence(context_risk, finding)
        
        # Determine risk level
        risk_level = self._score_to_risk_level(final_risk)
        
        # Generate assessment
        factors = self._identify_risk_factors(finding, context)
        recommendations = self._generate_recommendations(finding, risk_level)
        confidence = self._calculate_confidence(finding, context)
        severity = self._determine_severity(finding, risk_level)
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=final_risk,
            severity=severity,
            factors=factors,
            recommendations=recommendations,
            confidence=confidence,
            assessment_time=datetime.now(timezone.utc)
        )
    
    async def evaluate_cve_risk(self, finding: Dict[str, Any]) -> RiskLevel:
        """
        Simplified CVE risk evaluation for compatibility with tests
        
        Args:
            finding: CVE finding data
            
        Returns:
            RiskLevel based on CVSS score and other factors
        """
        cvss_score = finding.get('cvss_score', 0.0)
        
        # Map CVSS score to risk level
        risk_level = self._score_to_risk_level(cvss_score)
        
        # Apply CVE-specific modifiers
        if finding.get('cve_id'):
            cve_id = finding['cve_id']
            
            # Recent critical CVEs get elevated risk
            if cvss_score >= 9.0 and self._is_recent_cve(cve_id):
                risk_level = RiskLevel.CRITICAL
            
            # Well-known CVEs with active exploitation
            if cve_id in self._get_actively_exploited_cves():
                if risk_level.value < RiskLevel.HIGH.value:
                    risk_level = RiskLevel.HIGH
        
        return risk_level
    
    def _calculate_base_risk(self, finding: Dict[str, Any]) -> float:
        """Calculate base risk score from finding data"""
        base_score = 0.0
        
        # CVSS score (primary factor)
        cvss_score = finding.get('cvss_score', 0.0)
        if cvss_score > 0:
            base_score = cvss_score
        else:
            # Fallback to severity-based scoring
            severity = finding.get('severity', '').lower()
            severity_scores = {
                'critical': 9.5,
                'high': 7.5,
                'medium': 5.0,
                'low': 2.5,
                'info': 1.0
            }
            base_score = severity_scores.get(severity, 1.0)
        
        return base_score
    
    def _apply_context_modifiers(self, base_risk: float, finding: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Apply context-based risk modifiers"""
        modified_risk = base_risk
        
        # Environment factors
        environment = context.get('environment', 'unknown').lower()
        env_multipliers = {
            'production': 1.3,
            'staging': 1.1,
            'development': 0.8,
            'test': 0.7
        }
        modified_risk *= env_multipliers.get(environment, 1.0)
        
        # Network exposure
        exposure = context.get('network_exposure', 'internal').lower()
        exposure_multipliers = {
            'public': 1.4,
            'dmz': 1.2,
            'internal': 1.0,
            'isolated': 0.8
        }
        modified_risk *= exposure_multipliers.get(exposure, 1.0)
        
        # Service criticality
        criticality = context.get('service_criticality', 'medium').lower()
        criticality_multipliers = {
            'critical': 1.3,
            'high': 1.2,
            'medium': 1.0,
            'low': 0.9
        }
        modified_risk *= criticality_multipliers.get(criticality, 1.0)
        
        # Asset value
        asset_value = context.get('asset_value', 'medium').lower()
        asset_multipliers = {
            'high': 1.2,
            'medium': 1.0,
            'low': 0.9
        }
        modified_risk *= asset_multipliers.get(asset_value, 1.0)
        
        return min(modified_risk, 10.0)  # Cap at 10.0
    
    async def _apply_threat_intelligence(self, risk_score: float, finding: Dict[str, Any]) -> float:
        """Apply threat intelligence factors"""
        modified_risk = risk_score
        
        # CVE-specific threat intelligence
        cve_id = finding.get('cve_id')
        if cve_id:
            # Check if CVE is being actively exploited
            if cve_id in self._get_actively_exploited_cves():
                modified_risk *= 1.3
            
            # Apply age-based factors
            cve_age_days = self._get_cve_age_days(cve_id)
            age_factor = self._get_age_factor(cve_age_days)
            modified_risk *= age_factor
        
        # Tool-specific intelligence
        tool_name = finding.get('tool', '').lower()
        if tool_name == 'nuclei':
            # Nuclei templates are well-tested
            modified_risk *= 0.95
        elif tool_name == 'nmap':
            # Nmap findings are informational
            modified_risk *= 0.8
        
        return min(modified_risk, 10.0)
    
    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level"""
        for (min_score, max_score), risk_level in self.CVSS_RISK_MAPPING.items():
            if min_score <= score <= max_score:
                return risk_level
        
        return RiskLevel.LOW
    
    def _determine_severity(self, finding: Dict[str, Any], risk_level: RiskLevel) -> SeverityLevel:
        """Determine severity level from finding and risk assessment"""
        # Map risk level to severity
        risk_to_severity = {
            RiskLevel.LOW: SeverityLevel.LOW,
            RiskLevel.MEDIUM: SeverityLevel.MEDIUM,
            RiskLevel.HIGH: SeverityLevel.HIGH,
            RiskLevel.CRITICAL: SeverityLevel.CRITICAL
        }
        
        return risk_to_severity.get(risk_level, SeverityLevel.LOW)
    
    def _identify_risk_factors(self, finding: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Identify specific risk factors"""
        factors = []
        
        # CVSS-based factors
        cvss_score = finding.get('cvss_score', 0.0)
        if cvss_score >= 9.0:
            factors.append("Critical CVSS score (9.0+)")
        elif cvss_score >= 7.0:
            factors.append("High CVSS score (7.0-8.9)")
        
        # CVE factors
        cve_id = finding.get('cve_id')
        if cve_id:
            if self._is_recent_cve(cve_id):
                factors.append("Recently published CVE")
            if cve_id in self._get_actively_exploited_cves():
                factors.append("Known active exploitation")
        
        # Context factors
        if context.get('environment') == 'production':
            factors.append("Production environment")
        if context.get('network_exposure') == 'public':
            factors.append("Public network exposure")
        if context.get('service_criticality') == 'critical':
            factors.append("Critical service")
        
        # Finding-specific factors
        if finding.get('type') == 'rce':
            factors.append("Remote code execution potential")
        if 'authentication' in finding.get('name', '').lower():
            factors.append("Authentication bypass")
        if 'sql injection' in finding.get('name', '').lower():
            factors.append("SQL injection vulnerability")
        
        return factors
    
    def _generate_recommendations(self, finding: Dict[str, Any], risk_level: RiskLevel) -> List[str]:
        """Generate risk mitigation recommendations"""
        recommendations = []
        
        # Risk level based recommendations
        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "Immediate patching required",
                "Consider emergency change process",
                "Implement temporary mitigations",
                "Monitor for active exploitation"
            ])
        elif risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "Patch within 48-72 hours",
                "Implement network-level controls",
                "Increase monitoring"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "Patch within 1-2 weeks",
                "Review security controls",
                "Consider risk acceptance"
            ])
        else:
            recommendations.extend([
                "Patch during next maintenance window",
                "Document for compliance"
            ])
        
        # Finding-specific recommendations
        cve_id = finding.get('cve_id')
        if cve_id:
            recommendations.append(f"Review vendor advisory for {cve_id}")
        
        tool_name = finding.get('tool')
        if tool_name == 'nuclei':
            recommendations.append("Verify with manual testing")
        
        return recommendations
    
    def _calculate_confidence(self, finding: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate confidence score for the assessment"""
        confidence = 0.8  # Base confidence
        
        # Higher confidence for findings with CVSS scores
        if finding.get('cvss_score', 0) > 0:
            confidence += 0.1
        
        # Higher confidence for CVE findings
        if finding.get('cve_id'):
            confidence += 0.1
        
        # Lower confidence for tool-generated findings without manual verification
        if finding.get('tool') and not finding.get('manually_verified'):
            confidence -= 0.1
        
        # Context completeness affects confidence
        if len(context) > 3:
            confidence += 0.1
        elif len(context) < 2:
            confidence -= 0.1
        
        return max(0.1, min(1.0, confidence))
    
    def _is_recent_cve(self, cve_id: str) -> bool:
        """Check if CVE was published recently (last 90 days)"""
        # Simple heuristic based on CVE ID format (CVE-YYYY-NNNNN)
        try:
            year = int(cve_id.split('-')[1])
            current_year = datetime.now().year
            return year >= current_year - 1  # Last year or current year
        except:
            return False
    
    def _get_actively_exploited_cves(self) -> List[str]:
        """Get list of CVEs with known active exploitation"""
        # This would normally come from threat intelligence feeds
        return [
            'CVE-2021-44228',  # Log4Shell
            'CVE-2021-34527',  # PrintNightmare
            'CVE-2022-0543',   # Redis Lua RCE
            'CVE-2023-34362',  # MOVEit Transfer
        ]
    
    def _get_cve_age_days(self, cve_id: str) -> int:
        """Get age of CVE in days (simplified implementation)"""
        try:
            year = int(cve_id.split('-')[1])
            current_year = datetime.now().year
            return (current_year - year) * 365
        except:
            return 365  # Default to 1 year
    
    def _get_age_factor(self, age_days: int) -> float:
        """Get risk factor based on CVE age"""
        for days, factor in sorted(self.CVE_AGE_FACTORS.items()):
            if age_days <= days:
                return factor
        return 0.8  # Very old CVEs get reduced factor