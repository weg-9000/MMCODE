"""
Technology Version Compatibility Matrix

Provides version compatibility checking between technologies
to ensure recommended stacks are coherent and compatible.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class CompatibilityLevel(str, Enum):
    """Compatibility levels between technologies"""
    FULL = "full"           # Fully compatible, recommended combination
    PARTIAL = "partial"     # Compatible with some limitations
    EXPERIMENTAL = "experimental"  # Works but not production-ready
    INCOMPATIBLE = "incompatible"  # Known incompatibility
    UNKNOWN = "unknown"     # No compatibility data available


@dataclass
class VersionRange:
    """Represents a version range for compatibility"""
    min_version: Optional[str] = None
    max_version: Optional[str] = None

    def contains(self, version: str) -> bool:
        """Check if version is within range"""
        if not version:
            return True

        v = self._parse_version(version)

        if self.min_version:
            min_v = self._parse_version(self.min_version)
            if v < min_v:
                return False

        if self.max_version:
            max_v = self._parse_version(self.max_version)
            if v > max_v:
                return False

        return True

    def _parse_version(self, version: str) -> Tuple[int, ...]:
        """Parse version string to comparable tuple"""
        # Extract numeric parts
        parts = re.findall(r'\d+', version)
        return tuple(int(p) for p in parts[:3])  # Major.Minor.Patch


@dataclass
class CompatibilityRule:
    """Defines compatibility between two technologies"""
    tech_a: str
    tech_b: str
    level: CompatibilityLevel
    version_a: Optional[VersionRange] = None
    version_b: Optional[VersionRange] = None
    notes: str = ""
    recommended_together: bool = True


@dataclass
class TechMetadata:
    """Metadata about a technology"""
    name: str
    category: str
    latest_stable: str
    lts_version: Optional[str] = None
    eol_versions: List[str] = field(default_factory=list)
    min_recommended: str = ""
    ecosystem: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)


class CompatibilityMatrix:
    """
    Technology compatibility matrix for stack validation.

    Provides version compatibility checking and recommendations
    for coherent technology stack combinations.
    """

    def __init__(self):
        self._rules: Dict[str, Dict[str, CompatibilityRule]] = {}
        self._tech_metadata: Dict[str, TechMetadata] = {}
        self._load_compatibility_data()

    def check_compatibility(
        self,
        tech_a: str,
        tech_b: str,
        version_a: Optional[str] = None,
        version_b: Optional[str] = None
    ) -> Tuple[CompatibilityLevel, str]:
        """
        Check compatibility between two technologies.

        Args:
            tech_a: First technology name
            tech_b: Second technology name
            version_a: Version of first technology
            version_b: Version of second technology

        Returns:
            Tuple of (compatibility_level, notes)
        """
        key_a = tech_a.lower()
        key_b = tech_b.lower()

        # Check direct rule
        rule = self._get_rule(key_a, key_b)

        if not rule:
            # Check reverse rule
            rule = self._get_rule(key_b, key_a)
            if rule:
                version_a, version_b = version_b, version_a

        if not rule:
            return CompatibilityLevel.UNKNOWN, "No compatibility data available"

        # Check version constraints
        if version_a and rule.version_a:
            if not rule.version_a.contains(version_a):
                return CompatibilityLevel.PARTIAL, f"Version {version_a} may have compatibility issues"

        if version_b and rule.version_b:
            if not rule.version_b.contains(version_b):
                return CompatibilityLevel.PARTIAL, f"Version {version_b} may have compatibility issues"

        return rule.level, rule.notes

    def validate_stack(
        self,
        technologies: List[Tuple[str, Optional[str]]]
    ) -> Dict[str, any]:
        """
        Validate a complete technology stack for compatibility.

        Args:
            technologies: List of (tech_name, version) tuples

        Returns:
            Validation result with issues and recommendations
        """
        issues = []
        warnings = []
        recommendations = []

        # Check pairwise compatibility
        for i, (tech_a, ver_a) in enumerate(technologies):
            for tech_b, ver_b in technologies[i+1:]:
                level, notes = self.check_compatibility(tech_a, tech_b, ver_a, ver_b)

                if level == CompatibilityLevel.INCOMPATIBLE:
                    issues.append({
                        "tech_a": tech_a,
                        "tech_b": tech_b,
                        "level": level.value,
                        "message": notes or f"{tech_a} is incompatible with {tech_b}"
                    })
                elif level == CompatibilityLevel.PARTIAL:
                    warnings.append({
                        "tech_a": tech_a,
                        "tech_b": tech_b,
                        "level": level.value,
                        "message": notes or f"{tech_a} has limited compatibility with {tech_b}"
                    })
                elif level == CompatibilityLevel.EXPERIMENTAL:
                    warnings.append({
                        "tech_a": tech_a,
                        "tech_b": tech_b,
                        "level": level.value,
                        "message": notes or f"{tech_a} + {tech_b} combination is experimental"
                    })

        # Check for version recommendations
        for tech, version in technologies:
            metadata = self._tech_metadata.get(tech.lower())
            if metadata:
                if version and version in metadata.eol_versions:
                    issues.append({
                        "tech": tech,
                        "version": version,
                        "message": f"Version {version} is end-of-life. Upgrade recommended."
                    })
                elif metadata.lts_version and version != metadata.lts_version:
                    recommendations.append({
                        "tech": tech,
                        "current": version,
                        "recommended": metadata.lts_version,
                        "message": f"Consider using LTS version {metadata.lts_version}"
                    })

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
            "compatibility_score": self._calculate_compatibility_score(
                len(technologies), len(issues), len(warnings)
            )
        }

    def get_recommended_versions(self, tech: str) -> Dict[str, str]:
        """Get recommended versions for a technology"""
        metadata = self._tech_metadata.get(tech.lower())

        if not metadata:
            return {"status": "unknown"}

        return {
            "latest_stable": metadata.latest_stable,
            "lts": metadata.lts_version,
            "min_recommended": metadata.min_recommended,
            "ecosystem": metadata.ecosystem,
            "alternatives": metadata.alternatives
        }

    def get_compatible_technologies(
        self,
        tech: str,
        category: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """Get technologies compatible with the given one"""
        key = tech.lower()
        compatible = []

        # Check all rules involving this technology
        if key in self._rules:
            for other_tech, rule in self._rules[key].items():
                if rule.level in [CompatibilityLevel.FULL, CompatibilityLevel.PARTIAL]:
                    metadata = self._tech_metadata.get(other_tech)
                    if not category or (metadata and metadata.category == category):
                        compatible.append({
                            "name": other_tech,
                            "compatibility": rule.level.value,
                            "recommended": rule.recommended_together,
                            "notes": rule.notes
                        })

        return compatible

    def _get_rule(self, tech_a: str, tech_b: str) -> Optional[CompatibilityRule]:
        """Get compatibility rule between two technologies"""
        if tech_a in self._rules and tech_b in self._rules[tech_a]:
            return self._rules[tech_a][tech_b]
        return None

    def _add_rule(self, rule: CompatibilityRule):
        """Add a compatibility rule"""
        key_a = rule.tech_a.lower()
        key_b = rule.tech_b.lower()

        if key_a not in self._rules:
            self._rules[key_a] = {}

        self._rules[key_a][key_b] = rule

    def _calculate_compatibility_score(
        self,
        total_techs: int,
        issues: int,
        warnings: int
    ) -> float:
        """Calculate overall compatibility score"""
        if total_techs <= 1:
            return 1.0

        # Maximum possible compatibility checks
        max_checks = (total_techs * (total_techs - 1)) / 2

        if max_checks == 0:
            return 1.0

        # Deduct for issues and warnings
        penalty = (issues * 0.3 + warnings * 0.1) / max_checks

        return max(0.0, min(1.0, 1.0 - penalty))

    def _load_compatibility_data(self):
        """Load compatibility rules and metadata"""

        # === Technology Metadata ===

        # Frontend Frameworks
        self._tech_metadata["react"] = TechMetadata(
            name="React",
            category="frontend",
            latest_stable="18.2.0",
            lts_version="18.2.0",
            min_recommended="17.0.0",
            eol_versions=["15.x", "16.0", "16.1", "16.2"],
            ecosystem=["redux", "react-router", "react-query", "zustand"],
            alternatives=["vue", "angular", "svelte", "solid"]
        )

        self._tech_metadata["vue"] = TechMetadata(
            name="Vue",
            category="frontend",
            latest_stable="3.4.0",
            lts_version="3.4.0",
            min_recommended="3.0.0",
            eol_versions=["2.x"],
            ecosystem=["pinia", "vue-router", "vuex"],
            alternatives=["react", "angular", "svelte"]
        )

        self._tech_metadata["angular"] = TechMetadata(
            name="Angular",
            category="frontend",
            latest_stable="17.0.0",
            lts_version="16.0.0",
            min_recommended="15.0.0",
            eol_versions=["8.x", "9.x", "10.x", "11.x"],
            ecosystem=["ngrx", "angular-material", "rxjs"],
            alternatives=["react", "vue", "svelte"]
        )

        # Backend Frameworks
        self._tech_metadata["fastapi"] = TechMetadata(
            name="FastAPI",
            category="backend",
            latest_stable="0.109.0",
            min_recommended="0.100.0",
            ecosystem=["pydantic", "sqlalchemy", "alembic", "uvicorn"],
            alternatives=["django", "flask", "starlette"]
        )

        self._tech_metadata["django"] = TechMetadata(
            name="Django",
            category="backend",
            latest_stable="5.0.0",
            lts_version="4.2.0",
            min_recommended="4.0.0",
            eol_versions=["2.x", "3.0", "3.1"],
            ecosystem=["django-rest-framework", "celery", "django-channels"],
            alternatives=["fastapi", "flask"]
        )

        self._tech_metadata["express"] = TechMetadata(
            name="Express",
            category="backend",
            latest_stable="4.18.2",
            min_recommended="4.17.0",
            ecosystem=["passport", "mongoose", "sequelize"],
            alternatives=["fastify", "koa", "nestjs"]
        )

        self._tech_metadata["nestjs"] = TechMetadata(
            name="NestJS",
            category="backend",
            latest_stable="10.0.0",
            min_recommended="9.0.0",
            ecosystem=["typeorm", "prisma", "class-validator"],
            alternatives=["express", "fastify"]
        )

        # Databases
        self._tech_metadata["postgresql"] = TechMetadata(
            name="PostgreSQL",
            category="database",
            latest_stable="16.0",
            lts_version="15.0",
            min_recommended="13.0",
            eol_versions=["9.x", "10.x", "11.x"],
            ecosystem=["pgvector", "postgis", "timescaledb"],
            alternatives=["mysql", "mariadb"]
        )

        self._tech_metadata["mongodb"] = TechMetadata(
            name="MongoDB",
            category="database",
            latest_stable="7.0",
            min_recommended="6.0",
            eol_versions=["4.x", "5.0"],
            ecosystem=["mongoose", "motor", "pymongo"],
            alternatives=["postgresql", "dynamodb", "couchdb"]
        )

        self._tech_metadata["redis"] = TechMetadata(
            name="Redis",
            category="cache",
            latest_stable="7.2",
            min_recommended="6.0",
            eol_versions=["5.x"],
            ecosystem=["redis-om", "redis-py", "ioredis"],
            alternatives=["memcached", "dragonfly"]
        )

        self._tech_metadata["mysql"] = TechMetadata(
            name="MySQL",
            category="database",
            latest_stable="8.2",
            lts_version="8.0",
            min_recommended="8.0",
            eol_versions=["5.6", "5.7"],
            ecosystem=["mysql-connector", "mysqlclient"],
            alternatives=["postgresql", "mariadb"]
        )

        # Infrastructure
        self._tech_metadata["docker"] = TechMetadata(
            name="Docker",
            category="infrastructure",
            latest_stable="24.0",
            min_recommended="20.10",
            ecosystem=["docker-compose", "buildkit"],
            alternatives=["podman", "containerd"]
        )

        self._tech_metadata["kubernetes"] = TechMetadata(
            name="Kubernetes",
            category="infrastructure",
            latest_stable="1.29",
            min_recommended="1.27",
            eol_versions=["1.23", "1.24", "1.25"],
            ecosystem=["helm", "istio", "argocd"],
            alternatives=["docker-swarm", "nomad"]
        )

        # === Compatibility Rules ===

        # Frontend + Backend Combinations
        self._add_rule(CompatibilityRule(
            tech_a="react", tech_b="fastapi",
            level=CompatibilityLevel.FULL,
            notes="Excellent combination for modern SPAs with Python backend"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="react", tech_b="django",
            level=CompatibilityLevel.FULL,
            notes="Works well with Django REST Framework"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="react", tech_b="express",
            level=CompatibilityLevel.FULL,
            notes="Popular JavaScript full-stack combination"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="react", tech_b="nestjs",
            level=CompatibilityLevel.FULL,
            notes="TypeScript-first full-stack combination"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="vue", tech_b="fastapi",
            level=CompatibilityLevel.FULL,
            notes="Good combination for Python-based projects"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="vue", tech_b="django",
            level=CompatibilityLevel.FULL,
            notes="Works well with Django REST Framework"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="angular", tech_b="nestjs",
            level=CompatibilityLevel.FULL,
            notes="Both use TypeScript decorators, excellent synergy"
        ))

        # Backend + Database Combinations
        self._add_rule(CompatibilityRule(
            tech_a="fastapi", tech_b="postgresql",
            level=CompatibilityLevel.FULL,
            notes="Excellent with SQLAlchemy async support"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="fastapi", tech_b="mongodb",
            level=CompatibilityLevel.FULL,
            notes="Works well with motor async driver"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="django", tech_b="postgresql",
            level=CompatibilityLevel.FULL,
            notes="Django's preferred database choice"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="django", tech_b="mongodb",
            level=CompatibilityLevel.PARTIAL,
            notes="Requires djongo or mongoengine, limited ORM features",
            recommended_together=False
        ))

        self._add_rule(CompatibilityRule(
            tech_a="django", tech_b="mysql",
            level=CompatibilityLevel.FULL,
            notes="Full Django ORM support"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="express", tech_b="mongodb",
            level=CompatibilityLevel.FULL,
            notes="Classic MERN/MEAN stack combination"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="express", tech_b="postgresql",
            level=CompatibilityLevel.FULL,
            notes="Works well with Sequelize or TypeORM"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="nestjs", tech_b="postgresql",
            level=CompatibilityLevel.FULL,
            notes="Excellent with TypeORM integration"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="nestjs", tech_b="mongodb",
            level=CompatibilityLevel.FULL,
            notes="Great with Mongoose integration"
        ))

        # Cache Combinations
        self._add_rule(CompatibilityRule(
            tech_a="fastapi", tech_b="redis",
            level=CompatibilityLevel.FULL,
            notes="Excellent for caching and session management"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="django", tech_b="redis",
            level=CompatibilityLevel.FULL,
            notes="Great with django-redis for caching"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="express", tech_b="redis",
            level=CompatibilityLevel.FULL,
            notes="Excellent with ioredis"
        ))

        # Infrastructure Combinations
        self._add_rule(CompatibilityRule(
            tech_a="docker", tech_b="kubernetes",
            level=CompatibilityLevel.FULL,
            notes="Standard container orchestration stack"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="fastapi", tech_b="docker",
            level=CompatibilityLevel.FULL,
            notes="Excellent containerization support"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="django", tech_b="docker",
            level=CompatibilityLevel.FULL,
            notes="Well-documented containerization patterns"
        ))

        # Database Combinations
        self._add_rule(CompatibilityRule(
            tech_a="postgresql", tech_b="redis",
            level=CompatibilityLevel.FULL,
            notes="Common combination for caching layer"
        ))

        self._add_rule(CompatibilityRule(
            tech_a="mongodb", tech_b="redis",
            level=CompatibilityLevel.FULL,
            notes="Good for caching document queries"
        ))

        # Scale Warnings
        self._add_rule(CompatibilityRule(
            tech_a="sqlite", tech_b="kubernetes",
            level=CompatibilityLevel.INCOMPATIBLE,
            notes="SQLite not suitable for distributed deployments",
            recommended_together=False
        ))

        logger.info(
            f"Loaded {len(self._tech_metadata)} technology metadata entries "
            f"and {sum(len(rules) for rules in self._rules.values())} compatibility rules"
        )


# Singleton instance
_compatibility_matrix: Optional[CompatibilityMatrix] = None


def get_compatibility_matrix() -> CompatibilityMatrix:
    """Get singleton instance of CompatibilityMatrix"""
    global _compatibility_matrix
    if _compatibility_matrix is None:
        _compatibility_matrix = CompatibilityMatrix()
    return _compatibility_matrix
