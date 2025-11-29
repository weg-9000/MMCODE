"""
ThreatAnalyzer - MITRE ATT&CK Mapping Capability
==============================================

MITRE ATT&CK framework integration for mapping security findings
to tactics, techniques, and procedures (TTPs).
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from ....security.models import SecurityFinding, SeverityLevel, PentestPhase

logger = logging.getLogger(__name__)


class MitreTactic(Enum):
    """MITRE ATT&CK Tactics"""
    RECONNAISSANCE = "TA0043"
    RESOURCE_DEVELOPMENT = "TA0042"
    INITIAL_ACCESS = "TA0001"
    EXECUTION = "TA0002"
    PERSISTENCE = "TA0003"
    PRIVILEGE_ESCALATION = "TA0004"
    DEFENSE_EVASION = "TA0005"
    CREDENTIAL_ACCESS = "TA0006"
    DISCOVERY = "TA0007"
    LATERAL_MOVEMENT = "TA0008"
    COLLECTION = "TA0009"
    COMMAND_AND_CONTROL = "TA0011"
    EXFILTRATION = "TA0010"
    IMPACT = "TA0040"


@dataclass
class MitreTechnique:
    """MITRE ATT&CK Technique"""
    technique_id: str
    name: str
    tactic: MitreTactic
    description: str
    platforms: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    mitigation_ids: List[str] = field(default_factory=list)
    sub_techniques: List[str] = field(default_factory=list)


@dataclass
class AttackMapping:
    """Mapping between security finding and MITRE ATT&CK"""
    finding_id: str
    technique_id: str
    confidence: float  # 0.0-1.0
    evidence: List[str]
    context: str
    mapped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AttackPath:
    """Sequence of MITRE techniques forming an attack path"""
    path_id: str
    name: str
    techniques: List[MitreTechnique]
    likelihood: float
    impact_score: float
    prerequisites: List[str] = field(default_factory=list)
    countermeasures: List[str] = field(default_factory=list)


class MitreAttackMapping:
    """
    MITRE ATT&CK framework integration and mapping capability
    """
    
    # Comprehensive technique database (subset for demonstration)
    MITRE_TECHNIQUES = {
        "T1190": MitreTechnique(
            technique_id="T1190",
            name="Exploit Public-Facing Application",
            tactic=MitreTactic.INITIAL_ACCESS,
            description="Exploitation of weakness in Internet-facing computer or program",
            platforms=["Linux", "Windows", "macOS", "Network"],
            data_sources=["Application logs", "Web logs"],
            mitigation_ids=["M1048", "M1030", "M1016"]
        ),
        "T1059": MitreTechnique(
            technique_id="T1059",
            name="Command and Scripting Interpreter",
            tactic=MitreTactic.EXECUTION,
            description="Execution of commands and scripts",
            platforms=["Linux", "Windows", "macOS"],
            data_sources=["Process monitoring", "Command history"],
            sub_techniques=["T1059.001", "T1059.002", "T1059.003"],
            mitigation_ids=["M1038", "M1042"]
        ),
        "T1055": MitreTechnique(
            technique_id="T1055",
            name="Process Injection",
            tactic=MitreTactic.PRIVILEGE_ESCALATION,
            description="Injection of code into processes",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process monitoring", "API monitoring"],
            mitigation_ids=["M1040", "M1019"]
        ),
        "T1068": MitreTechnique(
            technique_id="T1068",
            name="Exploitation for Privilege Escalation",
            tactic=MitreTactic.PRIVILEGE_ESCALATION,
            description="Exploitation of software vulnerabilities to escalate privileges",
            platforms=["Linux", "Windows", "macOS"],
            data_sources=["Process monitoring", "System calls"],
            mitigation_ids=["M1048", "M1051"]
        ),
        "T1083": MitreTechnique(
            technique_id="T1083",
            name="File and Directory Discovery",
            tactic=MitreTactic.DISCOVERY,
            description="Enumeration of files and directories",
            platforms=["Linux", "Windows", "macOS"],
            data_sources=["File monitoring", "Process monitoring"],
            mitigation_ids=["M1028"]
        ),
        "T1078": MitreTechnique(
            technique_id="T1078",
            name="Valid Accounts",
            tactic=MitreTactic.INITIAL_ACCESS,
            description="Use of legitimate accounts for access",
            platforms=["Linux", "Windows", "macOS", "SaaS", "Office 365"],
            data_sources=["Authentication logs", "Account usage"],
            sub_techniques=["T1078.001", "T1078.002", "T1078.003", "T1078.004"],
            mitigation_ids=["M1027", "M1032", "M1018"]
        ),
        "T1110": MitreTechnique(
            technique_id="T1110",
            name="Brute Force",
            tactic=MitreTactic.CREDENTIAL_ACCESS,
            description="Attempts to guess passwords through automated trial and error",
            platforms=["Linux", "Windows", "macOS", "SaaS", "Office 365"],
            data_sources=["Authentication logs", "Account management"],
            sub_techniques=["T1110.001", "T1110.002", "T1110.003", "T1110.004"],
            mitigation_ids=["M1036", "M1032", "M1027"]
        ),
        "T1539": MitreTechnique(
            technique_id="T1539",
            name="Steal Web Session Cookie",
            tactic=MitreTactic.CREDENTIAL_ACCESS,
            description="Stealing session cookies to maintain access",
            platforms=["Linux", "Windows", "macOS"],
            data_sources=["Web logs", "Network traffic"],
            mitigation_ids=["M1054", "M1037"]
        ),
        "T1550": MitreTechnique(
            technique_id="T1550",
            name="Use Alternate Authentication Material",
            tactic=MitreTactic.LATERAL_MOVEMENT,
            description="Use of alternate authentication material",
            platforms=["Windows", "Office 365", "SaaS"],
            data_sources=["Authentication logs", "Logon session"],
            sub_techniques=["T1550.001", "T1550.002", "T1550.003", "T1550.004"],
            mitigation_ids=["M1027", "M1018"]
        ),
        "T1498": MitreTechnique(
            technique_id="T1498",
            name="Network Denial of Service",
            tactic=MitreTactic.IMPACT,
            description="Network-level denial of service attacks",
            platforms=["Linux", "Windows", "macOS", "Network"],
            data_sources=["Network traffic", "Netflow/Enclave netflow"],
            sub_techniques=["T1498.001", "T1498.002"],
            mitigation_ids=["M1037", "M1051"]
        ),
        "T1499": MitreTechnique(
            technique_id="T1499",
            name="Endpoint Denial of Service",
            tactic=MitreTactic.IMPACT,
            description="Endpoint-level denial of service attacks",
            platforms=["Linux", "Windows", "macOS"],
            data_sources=["Process monitoring", "System performance"],
            sub_techniques=["T1499.001", "T1499.002", "T1499.003", "T1499.004"],
            mitigation_ids=["M1037", "M1051"]
        ),
        "T1005": MitreTechnique(
            technique_id="T1005",
            name="Data from Local System",
            tactic=MitreTactic.COLLECTION,
            description="Collection of data from local system",
            platforms=["Linux", "Windows", "macOS"],
            data_sources=["File monitoring", "Process monitoring"],
            mitigation_ids=["M1057", "M1022"]
        ),
        "T1134": MitreTechnique(
            technique_id="T1134",
            name="Access Token Manipulation",
            tactic=MitreTactic.PRIVILEGE_ESCALATION,
            description="Manipulation of access tokens to escalate privileges",
            platforms=["Windows"],
            data_sources=["Process monitoring", "API monitoring"],
            sub_techniques=["T1134.001", "T1134.002", "T1134.003", "T1134.004", "T1134.005"],
            mitigation_ids=["M1026", "M1018"]
        )
    }
    
    # Vulnerability to technique mapping patterns
    VULNERABILITY_PATTERNS = {
        # Web Application Vulnerabilities
        "sql injection": ["T1190", "T1059"],
        "cross-site scripting": ["T1190", "T1055"],
        "xss": ["T1190", "T1055"], 
        "remote code execution": ["T1190", "T1059"],
        "rce": ["T1190", "T1059"],
        "command injection": ["T1190", "T1059"],
        "file upload": ["T1190", "T1083"],
        "directory traversal": ["T1083", "T1005"],
        "path traversal": ["T1083", "T1005"],
        "local file inclusion": ["T1083", "T1005"],
        "remote file inclusion": ["T1190", "T1083"],
        
        # Authentication & Session
        "authentication bypass": ["T1078", "T1110"],
        "session hijacking": ["T1539", "T1550"],
        "session fixation": ["T1539", "T1550"],
        "privilege escalation": ["T1068", "T1134"],
        "weak credentials": ["T1110", "T1078"],
        "default credentials": ["T1078", "T1110"],
        "brute force": ["T1110"],
        
        # Information Disclosure
        "information disclosure": ["T1083", "T1005"],
        "sensitive data exposure": ["T1083", "T1005"],
        "data leakage": ["T1083", "T1005"],
        
        # Denial of Service
        "denial of service": ["T1498", "T1499"],
        "dos": ["T1498", "T1499"],
        "resource exhaustion": ["T1499"],
        
        # Network & Protocol
        "buffer overflow": ["T1068", "T1055"],
        "stack overflow": ["T1068", "T1055"],
        "heap overflow": ["T1068", "T1055"],
        "format string": ["T1068", "T1059"],
        "memory corruption": ["T1068", "T1055"],
        
        # Configuration Issues
        "misconfiguration": ["T1190", "T1083"],
        "information leakage": ["T1083", "T1005"],
        "verbose error": ["T1083", "T1005"],
        "debug information": ["T1083", "T1005"]
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._mapping_cache: Dict[str, List[AttackMapping]] = {}
    
    def map_findings_to_mitre(self, 
                            findings: List[SecurityFinding]) -> List[AttackMapping]:
        """
        Map security findings to MITRE ATT&CK techniques
        
        Args:
            findings: Security findings to map
            
        Returns:
            List of MITRE ATT&CK mappings
        """
        self.logger.info(f"Mapping {len(findings)} findings to MITRE ATT&CK")
        
        mappings = []
        
        for finding in findings:
            # Check cache first
            cache_key = f"{finding.id}_{finding.title}_{finding.description}"
            if cache_key in self._mapping_cache:
                mappings.extend(self._mapping_cache[cache_key])
                continue
            
            # Generate new mappings
            finding_mappings = self._map_single_finding(finding)
            self._mapping_cache[cache_key] = finding_mappings
            mappings.extend(finding_mappings)
        
        return mappings
    
    def generate_attack_paths(self,
                            mappings: List[AttackMapping],
                            target_objective: str = "system_compromise") -> List[AttackPath]:
        """
        Generate potential attack paths from MITRE mappings
        
        Args:
            mappings: MITRE ATT&CK mappings
            target_objective: Target attack objective
            
        Returns:
            List of potential attack paths
        """
        self.logger.info(f"Generating attack paths for objective: {target_objective}")
        
        # Group mappings by tactic
        tactic_groups = {}
        for mapping in mappings:
            technique = self.MITRE_TECHNIQUES.get(mapping.technique_id)
            if technique:
                tactic = technique.tactic
                if tactic not in tactic_groups:
                    tactic_groups[tactic] = []
                tactic_groups[tactic].append((mapping, technique))
        
        # Generate logical attack sequences
        paths = []
        
        # Generate comprehensive attack path
        if self._has_sufficient_tactics(tactic_groups):
            comprehensive_path = self._generate_comprehensive_path(tactic_groups)
            if comprehensive_path:
                paths.append(comprehensive_path)
        
        # Generate focused paths by primary tactic
        for tactic, tactic_mappings in tactic_groups.items():
            focused_path = self._generate_focused_path(tactic, tactic_mappings)
            if focused_path:
                paths.append(focused_path)
        
        return paths
    
    def get_defensive_recommendations(self,
                                   mappings: List[AttackMapping]) -> Dict[str, List[str]]:
        """
        Generate defensive recommendations based on MITRE mappings
        
        Args:
            mappings: MITRE ATT&CK mappings
            
        Returns:
            Dictionary of defensive recommendations by category
        """
        recommendations = {
            "detection": [],
            "mitigation": [],
            "monitoring": [],
            "hardening": []
        }
        
        # Collect all techniques
        techniques = set(mapping.technique_id for mapping in mappings)
        
        for technique_id in techniques:
            technique = self.MITRE_TECHNIQUES.get(technique_id)
            if not technique:
                continue
            
            # Detection recommendations
            for data_source in technique.data_sources:
                rec = f"Monitor {data_source.lower()} for {technique.name}"
                if rec not in recommendations["detection"]:
                    recommendations["detection"].append(rec)
            
            # Mitigation recommendations
            for mitigation_id in technique.mitigation_ids:
                mitigation = self._get_mitigation_description(mitigation_id)
                if mitigation and mitigation not in recommendations["mitigation"]:
                    recommendations["mitigation"].append(mitigation)
            
            # Platform-specific hardening
            platform_hardening = self._get_platform_hardening(technique)
            recommendations["hardening"].extend(platform_hardening)
        
        # Remove duplicates and limit recommendations
        for category in recommendations:
            recommendations[category] = list(set(recommendations[category]))[:10]
        
        return recommendations
    
    def calculate_attack_coverage(self,
                                mappings: List[AttackMapping]) -> Dict[str, Any]:
        """
        Calculate MITRE ATT&CK coverage statistics
        
        Args:
            mappings: MITRE ATT&CK mappings
            
        Returns:
            Coverage statistics
        """
        # Count techniques by tactic
        tactic_counts = {}
        technique_ids = set()
        
        for mapping in mappings:
            technique = self.MITRE_TECHNIQUES.get(mapping.technique_id)
            if technique:
                tactic = technique.tactic
                tactic_counts[tactic] = tactic_counts.get(tactic, 0) + 1
                technique_ids.add(mapping.technique_id)
        
        # Calculate statistics
        total_techniques = len(technique_ids)
        covered_tactics = len(tactic_counts)
        total_tactics = len(MitreTactic)
        
        # Most common tactics
        sorted_tactics = sorted(tactic_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_techniques": total_techniques,
            "covered_tactics": covered_tactics,
            "total_tactics": total_tactics,
            "coverage_percentage": (covered_tactics / total_tactics) * 100,
            "tactic_distribution": {tactic.name: count for tactic, count in sorted_tactics},
            "most_common_tactics": [tactic.name for tactic, _ in sorted_tactics[:5]],
            "attack_surface_score": min(1.0, total_techniques / 20.0)  # Normalize to 0-1
        }
    
    def _map_single_finding(self, finding: SecurityFinding) -> List[AttackMapping]:
        """Map a single finding to MITRE techniques"""
        mappings = []
        
        # Normalize text for pattern matching
        title_lower = finding.title.lower()
        description_lower = finding.description.lower()
        combined_text = f"{title_lower} {description_lower}"
        
        # Find matching techniques
        matched_techniques = set()
        evidence_found = []
        
        for pattern, technique_ids in self.VULNERABILITY_PATTERNS.items():
            if pattern in combined_text:
                matched_techniques.update(technique_ids)
                evidence_found.append(f"Pattern '{pattern}' found in finding")
        
        # Create mappings for matched techniques
        for technique_id in matched_techniques:
            if technique_id in self.MITRE_TECHNIQUES:
                confidence = self._calculate_mapping_confidence(
                    finding, technique_id, evidence_found
                )
                
                mapping = AttackMapping(
                    finding_id=finding.id,
                    technique_id=technique_id,
                    confidence=confidence,
                    evidence=evidence_found.copy(),
                    context=self._generate_mapping_context(finding, technique_id)
                )
                mappings.append(mapping)
        
        return mappings
    
    def _calculate_mapping_confidence(self,
                                    finding: SecurityFinding,
                                    technique_id: str,
                                    evidence: List[str]) -> float:
        """Calculate confidence score for mapping"""
        confidence = 0.5  # Base confidence
        
        # Severity impact
        if finding.severity == SeverityLevel.CRITICAL:
            confidence += 0.2
        elif finding.severity == SeverityLevel.HIGH:
            confidence += 0.1
        
        # Evidence quality
        evidence_score = min(len(evidence) * 0.1, 0.3)
        confidence += evidence_score
        
        # CVE presence
        if finding.cve_id:
            confidence += 0.1
        
        # CVSS score
        if finding.cvss_score and finding.cvss_score >= 7.0:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_mapping_context(self,
                                finding: SecurityFinding,
                                technique_id: str) -> str:
        """Generate context for the mapping"""
        technique = self.MITRE_TECHNIQUES.get(technique_id)
        if not technique:
            return "Unknown technique"
        
        return (f"{finding.title} maps to {technique.name} "
                f"({technique.tactic.name}) with {finding.severity.name} severity")
    
    def _has_sufficient_tactics(self, tactic_groups: Dict[MitreTactic, List]) -> bool:
        """Check if we have sufficient tactics for comprehensive path"""
        required_tactics = [
            MitreTactic.INITIAL_ACCESS,
            MitreTactic.EXECUTION,
            MitreTactic.PERSISTENCE
        ]
        return all(tactic in tactic_groups for tactic in required_tactics)
    
    def _generate_comprehensive_path(self,
                                   tactic_groups: Dict[MitreTactic, List]) -> Optional[AttackPath]:
        """Generate comprehensive attack path"""
        # Typical attack sequence
        attack_sequence = [
            MitreTactic.RECONNAISSANCE,
            MitreTactic.INITIAL_ACCESS,
            MitreTactic.EXECUTION,
            MitreTactic.PRIVILEGE_ESCALATION,
            MitreTactic.PERSISTENCE,
            MitreTactic.CREDENTIAL_ACCESS,
            MitreTactic.DISCOVERY,
            MitreTactic.LATERAL_MOVEMENT,
            MitreTactic.COLLECTION,
            MitreTactic.EXFILTRATION
        ]
        
        path_techniques = []
        likelihood = 1.0
        impact_score = 0.0
        
        for tactic in attack_sequence:
            if tactic in tactic_groups:
                # Select highest confidence technique for this tactic
                best_mapping, best_technique = max(
                    tactic_groups[tactic],
                    key=lambda x: x[0].confidence
                )
                path_techniques.append(best_technique)
                likelihood *= best_mapping.confidence
                impact_score += self._get_technique_impact(best_technique)
        
        if not path_techniques:
            return None
        
        return AttackPath(
            path_id=f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name="Comprehensive Attack Path",
            techniques=path_techniques,
            likelihood=likelihood,
            impact_score=min(1.0, impact_score / len(path_techniques)),
            prerequisites=["Network access to target", "Basic reconnaissance"],
            countermeasures=self._generate_path_countermeasures(path_techniques)
        )
    
    def _generate_focused_path(self,
                             tactic: MitreTactic,
                             tactic_mappings: List[Tuple]) -> Optional[AttackPath]:
        """Generate focused attack path for specific tactic"""
        if not tactic_mappings:
            return None
        
        techniques = [technique for _, technique in tactic_mappings]
        avg_confidence = sum(mapping.confidence for mapping, _ in tactic_mappings) / len(tactic_mappings)
        
        return AttackPath(
            path_id=f"{tactic.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=f"{tactic.name.replace('_', ' ').title()} Focused Attack",
            techniques=techniques,
            likelihood=avg_confidence,
            impact_score=sum(self._get_technique_impact(t) for t in techniques) / len(techniques),
            prerequisites=[f"Access required for {tactic.name.lower()} phase"],
            countermeasures=self._generate_path_countermeasures(techniques)
        )
    
    def _get_technique_impact(self, technique: MitreTechnique) -> float:
        """Get impact score for technique"""
        impact_scores = {
            MitreTactic.INITIAL_ACCESS: 0.8,
            MitreTactic.EXECUTION: 0.7,
            MitreTactic.PRIVILEGE_ESCALATION: 0.9,
            MitreTactic.PERSISTENCE: 0.6,
            MitreTactic.CREDENTIAL_ACCESS: 0.8,
            MitreTactic.LATERAL_MOVEMENT: 0.7,
            MitreTactic.COLLECTION: 0.6,
            MitreTactic.EXFILTRATION: 0.9,
            MitreTactic.IMPACT: 1.0
        }
        return impact_scores.get(technique.tactic, 0.5)
    
    def _generate_path_countermeasures(self, techniques: List[MitreTechnique]) -> List[str]:
        """Generate countermeasures for attack path"""
        countermeasures = set()
        
        for technique in techniques:
            for mitigation_id in technique.mitigation_ids:
                mitigation = self._get_mitigation_description(mitigation_id)
                if mitigation:
                    countermeasures.add(mitigation)
        
        return list(countermeasures)[:10]  # Limit to top 10
    
    def _get_mitigation_description(self, mitigation_id: str) -> Optional[str]:
        """Get description for mitigation ID"""
        # Simplified mitigation mapping
        mitigations = {
            "M1048": "Application Isolation and Sandboxing",
            "M1030": "Network Segmentation",
            "M1016": "Vulnerability Scanning",
            "M1038": "Execution Prevention",
            "M1042": "Disable or Remove Feature or Program",
            "M1040": "Behavior Prevention on Endpoint",
            "M1019": "Threat Intelligence Program",
            "M1051": "Update Software",
            "M1028": "Operating System Configuration",
            "M1027": "Password Policies",
            "M1032": "Multi-factor Authentication",
            "M1018": "User Account Management",
            "M1036": "Account Use Policies",
            "M1054": "Software Configuration",
            "M1037": "Filter Network Traffic",
            "M1057": "Data Loss Prevention",
            "M1022": "Restrict File and Directory Permissions",
            "M1026": "Privileged Account Management"
        }
        return mitigations.get(mitigation_id)
    
    def _get_platform_hardening(self, technique: MitreTechnique) -> List[str]:
        """Get platform-specific hardening recommendations"""
        hardening = []
        
        if "Windows" in technique.platforms:
            hardening.append("Enable Windows Defender Advanced Threat Protection")
            hardening.append("Configure Windows Event Logging")
        
        if "Linux" in technique.platforms:
            hardening.append("Enable SELinux/AppArmor")
            hardening.append("Configure auditd for system monitoring")
        
        if "Network" in technique.platforms:
            hardening.append("Deploy network intrusion detection systems")
            hardening.append("Implement network segmentation")
        
        return hardening