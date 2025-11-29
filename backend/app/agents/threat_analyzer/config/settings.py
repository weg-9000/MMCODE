"""
ThreatAnalyzer Agent Configuration
=================================

Configuration settings for the PentestGPT-style threat analyzer agent
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from ...security.models import RiskLevel, PentestPhase


@dataclass
class ThreatAnalyzerConfig:
    """Configuration for ThreatAnalyzer agent"""
    
    # Agent identity
    agent_name: str = "ThreatAnalyzer"
    version: str = "2.0.0"
    
    # Operational settings
    max_concurrent_tasks: int = 3
    task_timeout_seconds: int = 3600  # 1 hour
    recommendation_limit: int = 10
    
    # PTT settings
    min_phase_completion_rate: float = 0.8  # 80% tasks must complete to advance phase
    max_tree_depth: int = 10
    max_tasks_per_phase: int = 50
    
    # Risk management
    default_risk_level: RiskLevel = RiskLevel.LOW
    auto_approval_risk_threshold: RiskLevel = RiskLevel.LOW
    require_human_approval: List[RiskLevel] = field(default_factory=lambda: [
        RiskLevel.MEDIUM, 
        RiskLevel.HIGH, 
        RiskLevel.CRITICAL
    ])
    
    # Tool configuration
    available_tools: List[str] = field(default_factory=lambda: [
        "nmap", "nuclei", "gobuster", "amass", "whois", "crt.sh", 
        "zap", "nikto", "dirb", "masscan", "rustscan"
    ])
    
    tool_paths: Dict[str, str] = field(default_factory=lambda: {
        "nmap": "/usr/bin/nmap",
        "nuclei": "/usr/bin/nuclei", 
        "gobuster": "/usr/bin/gobuster",
        "amass": "/usr/bin/amass"
    })
    
    # MITRE ATT&CK integration
    enable_mitre_mapping: bool = True
    mitre_framework_version: str = "v13"
    
    # Audit and compliance
    enable_audit_logging: bool = True
    audit_retention_days: int = 90
    compliance_mode: str = "strict"  # strict, standard, relaxed
    
    # Performance tuning
    task_batch_size: int = 5
    analysis_cache_ttl: int = 300  # 5 minutes
    priority_recalc_interval: int = 60  # 1 minute
    
    # LLM integration (optional)
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_max_tokens: int = 2000
    
    # Phase-specific settings
    phase_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        PentestPhase.RECONNAISSANCE.value: {
            "max_duration_hours": 4,
            "passive_only": True,
            "required_tools": ["amass", "whois"]
        },
        PentestPhase.SCANNING.value: {
            "max_duration_hours": 6,
            "rate_limit_per_second": 100,
            "required_tools": ["nmap"]
        },
        PentestPhase.ENUMERATION.value: {
            "max_duration_hours": 8,
            "directory_wordlist_size": 10000,
            "required_tools": ["gobuster"]
        },
        PentestPhase.VULNERABILITY_ASSESSMENT.value: {
            "max_duration_hours": 12,
            "scan_intensity": "medium",
            "required_tools": ["nuclei", "zap"]
        },
        PentestPhase.EXPLOITATION.value: {
            "max_duration_hours": 24,
            "require_explicit_approval": True,
            "backup_before_exploit": True
        },
        PentestPhase.POST_EXPLOITATION.value: {
            "max_duration_hours": 12,
            "evidence_collection": True,
            "cleanup_required": True
        },
        PentestPhase.REPORTING.value: {
            "max_duration_hours": 8,
            "include_remediation": True,
            "executive_summary": True
        }
    })


def get_threat_analyzer_config(**overrides) -> ThreatAnalyzerConfig:
    """Get ThreatAnalyzer configuration with optional overrides"""
    config = ThreatAnalyzerConfig()
    
    # Apply any overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config