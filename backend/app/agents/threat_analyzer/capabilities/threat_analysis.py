"""
ThreatAnalyzer - Threat Analysis Capability
==========================================

Core threat analysis functionality for identifying security threats,
vulnerabilities, and attack patterns.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

from ....security.models import (
    SecurityFinding,
    SeverityLevel, 
    PentestPhase,
    RiskLevel,
    ThreatVector
)

logger = logging.getLogger(__name__)


@dataclass
class ThreatProfile:
    """Profile of identified threats for a target"""
    target: str
    threat_vectors: List[ThreatVector]
    attack_surface_score: float
    risk_rating: RiskLevel
    key_vulnerabilities: List[SecurityFinding]
    recommended_priorities: List[str]
    analysis_timestamp: datetime


class ThreatAnalysisCapability:
    """
    Advanced threat analysis and vulnerability assessment capabilities
    """
    
    # OWASP Top 10 mapping
    OWASP_CATEGORIES = {
        "injection": {"priority": 1, "techniques": ["sqli", "nosqli", "ldapi", "os_injection"]},
        "broken_auth": {"priority": 2, "techniques": ["weak_passwords", "session_hijacking", "credential_stuffing"]},
        "sensitive_exposure": {"priority": 3, "techniques": ["data_leakage", "crypto_failures", "pii_exposure"]},
        "xml_entities": {"priority": 4, "techniques": ["xxe", "xml_bombs", "entity_expansion"]},
        "broken_access": {"priority": 5, "techniques": ["privilege_escalation", "idor", "path_traversal"]},
        "security_misconfig": {"priority": 6, "techniques": ["default_configs", "unnecessary_services", "verbose_errors"]},
        "xss": {"priority": 7, "techniques": ["stored_xss", "reflected_xss", "dom_xss"]},
        "insecure_deserial": {"priority": 8, "techniques": ["object_injection", "pickle_attacks"]},
        "known_vulnerabilities": {"priority": 9, "techniques": ["cve_exploitation", "outdated_components"]},
        "insufficient_logging": {"priority": 10, "techniques": ["log_injection", "missing_monitoring"]}
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._threat_intelligence_cache: Dict[str, Any] = {}
        
    def analyze_attack_surface(self, 
                             target: str,
                             services: List[Dict[str, Any]], 
                             findings: List[SecurityFinding]) -> ThreatProfile:
        """
        Analyze attack surface and generate threat profile
        
        Args:
            target: Target system identifier
            services: Discovered services and ports
            findings: Security findings from previous phases
            
        Returns:
            ThreatProfile with analysis results
        """
        self.logger.info(f"Analyzing attack surface for target: {target}")
        
        # Calculate attack surface score
        surface_score = self._calculate_attack_surface_score(services, findings)
        
        # Identify threat vectors
        threat_vectors = self._identify_threat_vectors(services, findings)
        
        # Assess risk rating
        risk_rating = self._assess_overall_risk(surface_score, findings)
        
        # Prioritize vulnerabilities
        key_vulnerabilities = self._prioritize_vulnerabilities(findings)
        
        # Generate recommendations
        recommendations = self._generate_threat_recommendations(
            threat_vectors, key_vulnerabilities
        )
        
        return ThreatProfile(
            target=target,
            threat_vectors=threat_vectors,
            attack_surface_score=surface_score,
            risk_rating=risk_rating,
            key_vulnerabilities=key_vulnerabilities[:10],  # Top 10
            recommended_priorities=recommendations,
            analysis_timestamp=datetime.now(timezone.utc)
        )
    
    def map_to_mitre_attack(self, 
                           findings: List[SecurityFinding]) -> Dict[str, List[str]]:
        """
        Map findings to MITRE ATT&CK framework techniques
        
        Args:
            findings: Security findings to map
            
        Returns:
            Dictionary mapping MITRE techniques to findings
        """
        mitre_mapping = {}
        
        for finding in findings:
            techniques = self._extract_mitre_techniques(finding)
            for technique in techniques:
                if technique not in mitre_mapping:
                    mitre_mapping[technique] = []
                mitre_mapping[technique].append(finding.id)
        
        return mitre_mapping
    
    def assess_exploitability(self, 
                            finding: SecurityFinding,
                            context: Dict[str, Any] = None) -> Tuple[float, str]:
        """
        Assess exploitability of a security finding
        
        Args:
            finding: Security finding to assess
            context: Additional context (network access, authentication, etc.)
            
        Returns:
            Tuple of (exploitability_score, reasoning)
        """
        score = 0.5  # Base score
        factors = []
        
        # Severity impact
        if finding.severity == SeverityLevel.CRITICAL:
            score += 0.3
            factors.append("Critical severity")
        elif finding.severity == SeverityLevel.HIGH:
            score += 0.2
            factors.append("High severity")
        
        # Network accessibility
        if context and context.get("network_accessible", True):
            score += 0.2
            factors.append("Network accessible")
        
        # Authentication required
        if context and not context.get("authentication_required", True):
            score += 0.2
            factors.append("No authentication required")
        
        # Public exploit availability
        if self._has_public_exploit(finding):
            score += 0.3
            factors.append("Public exploit available")
        
        # CVSS score consideration
        if finding.cvss_score and finding.cvss_score >= 7.0:
            score += 0.2
            factors.append(f"High CVSS score ({finding.cvss_score})")
        
        score = min(1.0, score)
        reasoning = " | ".join(factors) if factors else "Standard exploitability assessment"
        
        return score, reasoning
    
    def generate_exploit_chain(self, 
                             findings: List[SecurityFinding],
                             target_objective: str) -> List[Dict[str, Any]]:
        """
        Generate potential exploit chains for achieving target objective
        
        Args:
            findings: Available security findings
            target_objective: Target objective (e.g., "remote_code_execution")
            
        Returns:
            List of exploit chain steps
        """
        chains = []
        
        # Simple chain generation based on finding types
        for finding in findings:
            if finding.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
                chain_step = {
                    "step": len(chains) + 1,
                    "finding_id": finding.id,
                    "technique": finding.title,
                    "objective": self._map_to_objective(finding, target_objective),
                    "prerequisites": self._get_exploit_prerequisites(finding),
                    "impact": finding.impact,
                    "confidence": self._calculate_chain_confidence(finding)
                }
                chains.append(chain_step)
        
        # Sort by confidence and impact
        chains.sort(key=lambda x: (x["confidence"], x["impact"]), reverse=True)
        
        return chains[:5]  # Top 5 chains
    
    def _calculate_attack_surface_score(self, 
                                      services: List[Dict[str, Any]], 
                                      findings: List[SecurityFinding]) -> float:
        """Calculate attack surface exposure score (0.0-1.0)"""
        score = 0.0
        
        # Service exposure factor
        exposed_services = len([s for s in services if s.get("state") == "open"])
        service_factor = min(exposed_services * 0.1, 0.5)
        
        # Vulnerability factor
        vuln_count = len([f for f in findings if f.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]])
        vuln_factor = min(vuln_count * 0.15, 0.5)
        
        score = service_factor + vuln_factor
        return min(1.0, score)
    
    def _identify_threat_vectors(self, 
                               services: List[Dict[str, Any]], 
                               findings: List[SecurityFinding]) -> List[ThreatVector]:
        """Identify potential threat vectors"""
        vectors = []
        
        # Network-based vectors
        for service in services:
            if service.get("state") == "open":
                vector = ThreatVector(
                    vector_type="network",
                    entry_point=f"Port {service.get('port')}/{service.get('protocol', 'tcp')}",
                    service_name=service.get("service", "unknown"),
                    risk_level=RiskLevel.MEDIUM,
                    description=f"Network service exposure on {service.get('port')}"
                )
                vectors.append(vector)
        
        # Vulnerability-based vectors
        for finding in findings:
            if finding.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
                vector = ThreatVector(
                    vector_type="vulnerability",
                    entry_point=finding.affected_component,
                    service_name=finding.service_name or "unknown",
                    risk_level=self._severity_to_risk(finding.severity),
                    description=finding.title
                )
                vectors.append(vector)
        
        return vectors
    
    def _assess_overall_risk(self, 
                           surface_score: float, 
                           findings: List[SecurityFinding]) -> RiskLevel:
        """Assess overall risk level"""
        critical_count = len([f for f in findings if f.severity == SeverityLevel.CRITICAL])
        high_count = len([f for f in findings if f.severity == SeverityLevel.HIGH])
        
        if critical_count > 0 or surface_score > 0.8:
            return RiskLevel.CRITICAL
        elif high_count > 2 or surface_score > 0.6:
            return RiskLevel.HIGH
        elif high_count > 0 or surface_score > 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _prioritize_vulnerabilities(self, 
                                  findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Prioritize vulnerabilities by exploitability and impact"""
        def priority_score(finding):
            score = 0
            
            # Severity weight
            severity_weights = {
                SeverityLevel.CRITICAL: 40,
                SeverityLevel.HIGH: 30,
                SeverityLevel.MEDIUM: 20,
                SeverityLevel.LOW: 10
            }
            score += severity_weights.get(finding.severity, 0)
            
            # CVSS score
            if finding.cvss_score:
                score += finding.cvss_score * 5
            
            # Public exploit availability
            if self._has_public_exploit(finding):
                score += 20
            
            return score
        
        return sorted(findings, key=priority_score, reverse=True)
    
    def _generate_threat_recommendations(self, 
                                       threat_vectors: List[ThreatVector],
                                       vulnerabilities: List[SecurityFinding]) -> List[str]:
        """Generate threat mitigation recommendations"""
        recommendations = []
        
        # Vector-based recommendations
        network_vectors = [v for v in threat_vectors if v.vector_type == "network"]
        if network_vectors:
            recommendations.append("Implement network segmentation and access controls")
            recommendations.append("Review exposed services and close unnecessary ports")
        
        # Vulnerability-based recommendations
        critical_vulns = [v for v in vulnerabilities if v.severity == SeverityLevel.CRITICAL]
        if critical_vulns:
            recommendations.append("Immediately patch critical vulnerabilities")
            recommendations.append("Implement additional monitoring for critical assets")
        
        web_vulns = [v for v in vulnerabilities if "web" in v.category.lower()]
        if web_vulns:
            recommendations.append("Deploy Web Application Firewall (WAF)")
            recommendations.append("Implement secure coding practices")
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _extract_mitre_techniques(self, finding: SecurityFinding) -> List[str]:
        """Extract MITRE ATT&CK techniques from finding"""
        techniques = []
        
        # Simple keyword-based mapping
        title_lower = finding.title.lower()
        description_lower = finding.description.lower()
        
        technique_mapping = {
            "sql injection": ["T1190", "T1059"],
            "cross-site scripting": ["T1190", "T1055"],
            "remote code execution": ["T1190", "T1059"],
            "privilege escalation": ["T1068", "T1134"],
            "directory traversal": ["T1083", "T1005"],
            "authentication bypass": ["T1078", "T1110"],
            "session hijacking": ["T1539", "T1550"],
            "information disclosure": ["T1083", "T1005"],
            "denial of service": ["T1498", "T1499"]
        }
        
        for pattern, mitre_techniques in technique_mapping.items():
            if pattern in title_lower or pattern in description_lower:
                techniques.extend(mitre_techniques)
        
        return list(set(techniques))  # Remove duplicates
    
    def _has_public_exploit(self, finding: SecurityFinding) -> bool:
        """Check if public exploit exists for finding"""
        # Simplified check based on CVE or common vulnerability patterns
        if finding.cve_id:
            return True  # Assume CVEs have potential public exploits
        
        high_risk_patterns = [
            "remote code execution",
            "buffer overflow", 
            "sql injection",
            "authentication bypass",
            "privilege escalation"
        ]
        
        title_lower = finding.title.lower()
        return any(pattern in title_lower for pattern in high_risk_patterns)
    
    def _severity_to_risk(self, severity: SeverityLevel) -> RiskLevel:
        """Convert severity to risk level"""
        mapping = {
            SeverityLevel.CRITICAL: RiskLevel.CRITICAL,
            SeverityLevel.HIGH: RiskLevel.HIGH,
            SeverityLevel.MEDIUM: RiskLevel.MEDIUM,
            SeverityLevel.LOW: RiskLevel.LOW
        }
        return mapping.get(severity, RiskLevel.LOW)
    
    def _map_to_objective(self, finding: SecurityFinding, objective: str) -> str:
        """Map finding to target objective"""
        if "code execution" in finding.title.lower():
            return "remote_code_execution"
        elif "privilege" in finding.title.lower():
            return "privilege_escalation"
        elif "authentication" in finding.title.lower():
            return "authentication_bypass"
        else:
            return "information_gathering"
    
    def _get_exploit_prerequisites(self, finding: SecurityFinding) -> List[str]:
        """Get prerequisites for exploiting finding"""
        prereqs = []
        
        if "authentication" not in finding.title.lower():
            prereqs.append("Network access to target")
        else:
            prereqs.append("Valid user credentials")
        
        if finding.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
            prereqs.append("Target service availability")
        
        return prereqs
    
    def _calculate_chain_confidence(self, finding: SecurityFinding) -> float:
        """Calculate confidence in exploit chain step"""
        confidence = 0.5  # Base confidence
        
        if finding.cvss_score and finding.cvss_score >= 7.0:
            confidence += 0.2
        
        if self._has_public_exploit(finding):
            confidence += 0.3
        
        if finding.severity == SeverityLevel.CRITICAL:
            confidence += 0.2
        
        return min(1.0, confidence)